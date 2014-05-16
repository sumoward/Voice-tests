from selection.BeginAssignment import BeginAssignment
from vocollect_core.task.task import TaskBase

from vocollect_core.dialog.functions import prompt_yes_no, prompt_ready
from vocollect_core import itext, obj_factory, class_factory
from common.VoiceLinkLut import VoiceLinkLutOdr
from selection.GetContainerPrintLabel import GetContainerPrintLabel
from selection.SharedConstants import BEGIN_ASSIGNMENT_TASK_NAME,\
    BEGIN_ASSIGN_SUMMARY, BEGIN_ASSIGN_PRINT, BEGIN_ASSIGN_BASE_INTIALIIZE,\
    BEGIN_ASSIGN_BASE_START, BEGIN_ASSIGN_BASE_NEXT, BEGIN_ASSIGN_BASE_PROMPT,\
    BEGIN_ASSIGN_BASE_PICK

import logging #@UnresolvedImport
#logging.basicConfig(level=logging.DEBUG)


class BeginAssignment_Custom(BeginAssignment):
    pass
    logging.debug('**Begin assignment')
    ''' Begin assignment task for selection. initializes assignments 
    and speaks assignment summary, opens containers, and does base item reviews
    
    Steps:
            1. Assignment Summary 
            2. Print labels/Open containers
            3. Base item summary
     Parameters
            region - region operator is picking in 
            assignment_lut - assignments currently working on
            picks_lut - picks for assignments
            container_lut - container for assignment
            taskRunner (Default = None) - Task runner object
            callingTask (Default = None) - Calling task (should be a pick prompt task)
    '''

    def __init__(self, region,  assignment_lut, picks_lut,
                 container_lut, 
                 taskRunner = None, callingTask = None):
        
        #Sets region before TaskBase init
        super(BeginAssignment, self).__init__(taskRunner, callingTask)

        #Set task name
        self.name = BEGIN_ASSIGNMENT_TASK_NAME
        
        #working variables
        self._region = region
        
        #define LUTs
        self._assignment_lut = assignment_lut
        self._container_lut = container_lut
        self._picks_lut = picks_lut
        self._update_status_lut = VoiceLinkLutOdr('prTaskLUTUpdateStatus', 'prTaskODRUpdateStatus', self._region['useLuts'])
        

        #base item working variables
        self.all_base_items = []
        self.base_item_iter = None
        self.base_pick = None
        
    def initializeStates(self):
        ''' Initialize States and build LUTs '''
        
        self.addState(BEGIN_ASSIGN_SUMMARY,         self.summmary_prompt)
        self.addState(BEGIN_ASSIGN_PRINT,           self.print_labels)
        self.addState(BEGIN_ASSIGN_BASE_INTIALIIZE, self.base_item_summary_initialize)
        self.addState(BEGIN_ASSIGN_BASE_START,      self.base_item_summary_start)
        self.addState(BEGIN_ASSIGN_BASE_NEXT,       self.base_item_summary_next)
        self.addState(BEGIN_ASSIGN_BASE_PROMPT,     self.base_item_summary_prompt)
        self.addState(BEGIN_ASSIGN_BASE_PICK,       self.base_item_summary_pick)
    
    #----------------------------------------------------------
    def summmary_prompt(self):
        ''' speak the summary prompt for all the assignments '''
        logging.debug('--Summary prompt in begin')
        for assignment in self._assignment_lut:
            prompt = ''
            #check if override prompt set, that one was given
            if assignment['summaryPromptType'] == 2 and assignment['overridePrompt'] == '':
                assignment['summaryPromptType'] = 0
            
            #build prompt
            if assignment['summaryPromptType'] == 0: #Default Prompt
                prompt_key = 'summary.prompt'
                prompt_values = [assignment['idDescription']]
                #check if chase
                if assignment['isChase'] == '1': 
                    prompt_key += '.chase'
                
                #check if multiple assignments
                if len(self._assignment_lut) > 1:
                    prompt_key += '.position'
                    prompt_values.insert(0, assignment['position'])
                
                #check if goal time
                if assignment['goalTime'] != 0:
                    prompt_values.append(assignment['goalTime'])
                    if assignment['goalTime'] == 1:
                        prompt_key += '.goaltime.single'
                    else:
                        prompt_key += '.goaltime.multi'

                prompt = itext(prompt_key, *prompt_values)

            elif assignment['summaryPromptType'] == 2: #OverridePrompt
                prompt = assignment['overridePrompt']
                
            if prompt != '': #May be blank is summaryPromptType = 1
                prompt_ready(prompt, True)

    #----------------------------------------------------------
    def print_labels(self):
        ''' print labels '''
        logging.debug('--label print in begin')
        self.launch(obj_factory.get(GetContainerPrintLabel,
                                      self._region,
                                      self._assignment_lut, 
                                      self._picks_lut,
                                      self._container_lut,
                                      self.taskRunner, 
                                      self))
     
    #----------------------------------------------------------
    def base_item_summary_initialize(self):
        ''' initialize base item variables '''
        logging.debug('--base item in begin')
        self.all_base_items = []
        sequences = [] #list of picks that were already added
        for pick in self._picks_lut:
            if pick['status'] == 'B':
                if pick['sequence'] not in sequences: 
                    sequences.append(pick['sequence'])
                    base_item = {} #a base item summary object
                    base_item['preAisle'] = pick['preAisle']
                    base_item['aisle'] = pick['aisle']
                    base_item['postAisle'] = pick['postAisle']
                    base_item['slot'] = pick['slot']
                    base_item['description'] = pick['description']
                    base_item['qtyToPick'] = pick['qtyToPick']
                    base_item['idDescription'] = pick['idDescription']
                    #add any matching picks quantity
                    for match_pick in self._picks_lut:
                        if match_pick['sequence'] not in sequences: 
                            if self._picks_lut.picks_match(pick, match_pick):
                                sequences.append(match_pick['sequence'])
                                base_item['qtyToPick'] += match_pick['qtyToPick']

                
                    self.all_base_items.append(base_item)


    #----------------------------------------------------------
    def base_item_summary_start(self):
        ''' check if base items exist and start prompts '''

        #check base items exist and if operator wants to here summary
        if len(self.all_base_items) > 0:
            if prompt_yes_no(itext('selection.base.summary')):
                self.base_item_iter = iter(self.all_base_items)
            else:
                self.next_state = BEGIN_ASSIGN_BASE_PICK
        else:
            #no base items so just end
            self.next_state = ''

    #----------------------------------------------------------
    def base_item_summary_next(self):
        ''' check for next base item '''
        try:
            #see if there is another base item
            self.base_pick = next(self.base_item_iter)
        except:
            self.next_state = BEGIN_ASSIGN_BASE_PICK
        
    #----------------------------------------------------------
    def base_item_summary_prompt(self):
        ''' prompt for base item ''' 
        
        #set/determine if ID description is needed
        id_description = ''
        if self._region['containerType'] == 0 and self._assignment_lut.has_multiple_assignments():
            id_description = self.base_pick['idDescription']
        
        #get proper prompt key to speak (with or without ID)
        prompt_key = 'selection.base.summary.prompt'
        if self.base_pick['preAisle'] =='':
            prompt_key = 'selection.base.summary.prompt.nopreaisle'
            
        if self.base_pick['aisle'] =='':
            prompt_key = 'selection.base.summary.prompt.noaisle'
            
        if self.base_pick['postAisle'] =='':
            prompt_key = 'selection.base.summary.prompt.nopostaisle'    
            
        if self.base_pick['preAisle'] =='' and self.base_pick['aisle'] == '':
            prompt_key = 'selection.base.summary.prompt.nopreaisle.noaisle'
            
        if self.base_pick['preAisle'] =='' and self.base_pick['aisle'] == '' and self.base_pick['postAisle'] == '':
            prompt_key = 'selection.base.summary.prompt.nopreaisle.noaisle.nopostaisle'
            
                
        if id_description != '':
            prompt_key = 'selection.base.summary.prompt.id'
            
            if self.base_pick['preAisle'] =='':
                prompt_key = 'selection.base.summary.prompt.nopreaisle.id'
            
            if self.base_pick['aisle'] =='':
                prompt_key = 'selection.base.summary.prompt.noaisle.id'
            
            if self.base_pick['postAisle'] =='':
                prompt_key = 'selection.base.summary.prompt.nopostaisle.id'    
            
            if self.base_pick['preAisle'] =='' and self.base_pick['aisle'] == '':
                prompt_key = 'selection.base.summary.prompt.nopreaisle.noaisle.id'
            
            if self.base_pick['preAisle'] =='' and self.base_pick['aisle'] == '' and self.base_pick['postAisle'] == '':
                prompt_key = 'selection.base.summary.prompt.nopreaisle.noaisle.nopostaisle.id'
      
            

        #prompt information
        response = prompt_ready(itext(prompt_key,
                                      self.base_pick['preAisle'],
                                      self.base_pick['aisle'],
                                      self.base_pick['postAisle'],
                                      self.base_pick['slot'],
                                      self.base_pick['description'].lower(),
                                      id_description,
                                      self.base_pick['qtyToPick']),
                                False, 
                                ['cancel'])
        

        self.next_state = BEGIN_ASSIGN_BASE_NEXT
        if response == 'cancel':
            if prompt_yes_no(itext('selection.base.summary.cancel')):
                self.next_state = None
            else:
                self.next_state = BEGIN_ASSIGN_BASE_PROMPT                
    #----------------------------------------------------------
    def base_item_summary_pick(self):
        ''' ask operator if they want to pick base items '''
        
        #if operator want to pick base items then no more states need exectured
        if not prompt_yes_no(itext('selection.pick.base.items')):
            result = self._update_status_lut.do_transmit(self._assignment_lut[0]['groupID'],
                                                         '',
                                                         '2', #all picks in assignment
                                                         'N') #set to not picked
                    
            #If no errors, update picks, otherwise try again
            if result != 0:
                self.next_state = BEGIN_ASSIGN_BASE_PICK
            else:
                for pick in self._picks_lut:
                    if pick['status'] == 'B':
                        pick['status'] = 'N'
                        

obj_factory.set_override(BeginAssignment, BeginAssignment_Custom)