from vocollect_core.utilities import obj_factory
from selection.PickAssignment import PickAssignmentTask
from vocollect_core.task.task import TaskBase

from vocollect_core.dialog.functions import prompt_yes_no, prompt_only, prompt_ready
from common.VoiceLinkLut import VoiceLinkLutOdr, VoiceLinkLut
from vocollect_core import itext, obj_factory, class_factory
from selection.PickPromptSingle import PickPromptSingleTask
from selection.PickPromptMultiple import PickPromptMultipleTask
from selection.SharedConstants import PICK_ASSIGNMENT_TASK_NAME,\
    PICK_ASSIGNMENT_CHECK_NEXT_PICK, VERIFY_LOCATION_REPLEN,\
    PICK_ASSIGNMENT_PREAISLE, PICK_ASSIGNMENT_AISLE, PICK_ASSIGNMENT_POSTAISLE,\
    PICK_ASSIGNMENT_PICKPROMPT, PICK_ASSIGNMENT_END_PICKING
    
import logging #@UnresolvedImport
#logging.basicConfig(level=logging.DEBUG)

class PickAssignmentTask_Custom(PickAssignmentTask):
    pass
    logging.debug('**Pick Assignment custom')
    '''Pick an assignment 
    
     Steps:
            1. Check for pick
            2, verify location replenishment
            3. Pre-aisle prompt
            4. Aisle prompt
            5. Post aisle prompt
            6. Pick prompt
            7. Check end picking  
          
     Parameters
            region - region operator is picking in 
            assignment_lut - assignments currently working on
            picks_lut - pick list
            container_lut - current list of containers
            taskRunner (Default = None) - Task runner object
            callingTask (Default = None) - Calling task (should be a pick prompt task)
    '''

    #----------------------------------------------------------
    def __init__(self, 
                 taskRunner = None, 
                 callingTask = None):
        super(PickAssignmentTask, self).__init__(taskRunner, callingTask)

        #Set task name
        self.name = PICK_ASSIGNMENT_TASK_NAME

        self._region = None
        self._assignment_lut = None
        self._picks_lut = None
        self._container_lut = None
        self._pickList = []
        self._auto_short = False
        
        self._verify_loc_lut = obj_factory.get(VoiceLinkLut, 'prTaskLUTVerifyReplenishment')
        self._pick_prompt_task = None
        
    #----------------------------------------------------------
    def configure(self, 
                  region, 
                  assignment_lut, 
                  picks_lut,
                  container_lut,
                  pick_only):
        ''' Configures object so it can run an assignment and set of picks '''
        logging.debug('--Pick Assignment Configure')
        #clear previous pick prompt object
        self._pick_prompt_task = None
        
        #intialize objects
        self._region = region
        self._assignment_lut = assignment_lut
        self._picks_lut = picks_lut
        self._container_lut = container_lut
         
        self._pickList = []
        self._auto_short = False

        #define pick mode
        if self._picks_lut.has_picks(None, ['B']):
            self.status='B'
        else:
            self.status='N'

        #Do not clear previous information if pick by pick mode
        # and on a subsequent pick request (pick_only = true)
        if pick_only and self._region['pickByPick']:
            pass
        else:
            self._aisle_direction=''
            self._pre_aisle_direction=''
            self._post_aisle_direction=''

        #reset states
        self.current_state = None
        self.next_state = None
         
    #----------------------------------------------------------
    def initializeStates(self):
        ''' Initialize States'''
        self.addState(PICK_ASSIGNMENT_CHECK_NEXT_PICK, self.check_next_pick)
        self.addState(VERIFY_LOCATION_REPLEN, self.verify_location_replenished)
        self.addState(PICK_ASSIGNMENT_PREAISLE, self.pre_aisle)
        
        logging.debug('--aisle verification disabled.')
        #uncomment to allow aisle verification
        #self.addState(PICK_ASSIGNMENT_AISLE, self.aisle)
        self.addState(PICK_ASSIGNMENT_POSTAISLE, self.post_aisle)
        self.addState(PICK_ASSIGNMENT_PICKPROMPT, self.pick_prompt)
        self.addState(PICK_ASSIGNMENT_END_PICKING, self.end_picking)

    #----------------------------------------------------------
    def check_next_pick(self):
        ''' Checks next pick'''
        logging.debug('--Pick Assignment next pick')
        #check for next pick
        self._auto_short = False
        
        # Holds the complete next pick list at the end
        self._pickList = []
        
        # Holds the first pick found with the right status
        first_pick = None
        
        # Holds candidates for matching picks
        candidates = []
        
        if self._region['containerType'] == 0:
            combine_assignments = False
        else:
            combine_assignments = True
        
        # Search for a pick with the correct status. Process all picks in
        # the LUT, remembering possible match candidates.    
        for pick in self._picks_lut:
            if pick['status'] == self.status and first_pick == None:
                first_pick = pick;
                self._pickList.append(pick)
            elif pick['status'] != 'P':
                # This is a match candidate
                candidates.append(pick)

    
        if first_pick != None:               
            #Check for any matching picks among the candidates
            if len(candidates) > 0:
                for pick in candidates:
                    if self._picks_lut.picks_match(first_pick, pick, combine_assignments): 
                        self._pickList.append(pick)
                        pick['status'] = first_pick['status']

            self.dynamic_vocab.next_pick(self._pickList)   
        else:
            #No more picks
            self.next_state = PICK_ASSIGNMENT_END_PICKING
        
    #----------------------------------------------------------
    def verify_location_replenished(self):
        logging.debug('--Pick Assignment verify location replenished')
        if self._pickList[0]['verifyLocation'] != 0:
            if self._verify_loc_lut.do_transmit(self._pickList[0]['locationID'],
                                                self._pickList[0]['itemNumber']) == 0:
                self._pickList[0]['verifyLocation'] = 0
                if not self._verify_loc_lut[0]['replenished']:
                    self._auto_short = True
                    self.next_state = PICK_ASSIGNMENT_PICKPROMPT
            else:
                self.next_state = VERIFY_LOCATION_REPLEN
        
    #----------------------------------------------------------     
    def pre_aisle(self):
        ''' directing to Pre Aisle'''
        logging.debug('--Pick Assignment pre aisle')
        #if pre-aisle is same as pre-aisle don't prompt
        if self._pickList[0]["preAisle"] != self._pre_aisle_direction:
            if self._pickList[0]["preAisle"] != '':
                prompt_ready(itext('selection.pick.assignment.preaisle', 
                                        self._pickList[0]["preAisle"]),True)

            self._post_aisle_direction=''
            self._aisle_direction=''
            self._pre_aisle_direction = self._pickList[0]["preAisle"]


    #----------------------------------------------------------
    def aisle(self):
        ''' directing to Aisle'''
        logging.debug('--Pick Assignment Aisle')
        #if aisle is same as aisle don't prompt
        result = ''
        if self._pickList[0]["aisle"] != self._aisle_direction:
            if self._pickList[0]["aisle"] != '':
                result = prompt_ready(itext('selection.pick.assignment.aisle', 
                                                 self._pickList[0]["aisle"]), True,
                                                 {'skip aisle' : False})
                if result == 'skip aisle':
                    self.next_state = PICK_ASSIGNMENT_AISLE
                    self._skip_aisle()

            if result != 'skip aisle':
                self._post_aisle_direction=''
                self._aisle_direction = self._pickList[0]["aisle"]

                    
                                       
    #----------------------------------------------------------
    def post_aisle(self):
        ''' directing to Post Aisle'''
        #if aisle is same as post-aisle don't prompt
        if self._pickList[0]["postAisle"] != self._post_aisle_direction: 
            if self._pickList[0]["postAisle"] != '':
                prompt_ready(itext('selection.pick.assignment.postaisle', 
                                        self._pickList[0]["postAisle"]), True)

            self._post_aisle_direction = self._pickList[0]["postAisle"]

    #----------------------------------------------------------        
    def pick_prompt(self):
        logging.debug('--Pick Assignment pick prompt')
        '''Pick prompt Multiple and single'''
        if self._pick_prompt_task is None:
            if(self._region['pickPromptType'] == '2'):
                logging.debug('pick multi1')
                self._pick_prompt_task = obj_factory.get(PickPromptMultipleTask,
                                              self._region,
                                              self._assignment_lut, 
                                              self._pickList,
                                              self._container_lut, 
                                              self._auto_short,
                                              self.taskRunner, self)
            else:
                logging.debug('--Pick prompt single in Pick assignment task custom')
                self._pick_prompt_task = obj_factory.get(PickPromptSingleTask,
                                              self._region,
                                              self._assignment_lut, 
                                              self._pickList,
                                              self._container_lut, 
                                              self._auto_short,
                                              self.taskRunner, self)
        else:
            self._pick_prompt_task.config(self._pickList,
                                          self._auto_short)
        self.launch(self._pick_prompt_task,
                PICK_ASSIGNMENT_CHECK_NEXT_PICK)
     
    #----------------------------------------------------------        
    def end_picking(self):
        ''' End Picking'''
        logging.debug('--Pick Assignment end_picking')
        #end picking
        if self.status == 'B':
            self.status = 'N'
            self.next_state = PICK_ASSIGNMENT_CHECK_NEXT_PICK
            self._update_status('', 2, 'N')
        elif self.status == 'N':
            if not self._region['pickByPick']:
                if self._picks_lut.has_picks(None, ['N', 'S']):
                    for pick in self._picks_lut:
                        if pick['status'] == 'S':
                            pick['status'] = 'N'
                    self.next_state = PICK_ASSIGNMENT_CHECK_NEXT_PICK
                    self._update_status('', 2, 'N')
                else:
                    prompt_only(itext('selection.pick.assignment.picking.complete'))    
        else:
            self.dynamic_vocab.next_pick([])

    #----------------------------------------------------------        
    def _update_status(self, location, scope, status):
        ''' sends an update status '''
        logging.debug('--Pick Assignment update status')
        #send update status
        update_status = VoiceLinkLutOdr('prTaskLUTUpdateStatus', 
                                        'prTaskODRUpdateStatus', 
                                        self._region['useLuts'])
        while update_status.do_transmit(self._assignment_lut[0]['groupID'],
                                        location,
                                        scope, status) != 0:
            pass
        
        
    #----------------------------------------------------------        
    def _skip_aisle(self):
        ''' method to process the skip aisle command when spoken '''
        logging.debug('--Pick Assignment skip isle')
        #check if region allows
        if not self._region['skipAisleAllowed']:
            prompt_only(itext('generic.skip.aisle.notallowed'))
            return
         
        #check if another aisle
        curr_pre_aisle = self._pickList[0]['preAisle']
        curr_aisle = self._pickList[0]['aisle']
        allowed = False
        pass_status = 'N'
        skip_status = 'S'
        if not self._region['pickByPick']:
            for pick in self._picks_lut:
                if (pick['status'] not in ['P', 'X'] 
                    and (pick['preAisle'] != curr_pre_aisle 
                         or pick['aisle'] != curr_aisle)):
                    allowed = True

                if pick['status'] == 'B': #must be in base item pass
                    pass_status = 'B'
                    skip_status = 'N'
            
                #last aisle not allowed to skip
            if not allowed:
                prompt_only(itext('generic.skip.aisle.last'))
                self._aisle_direction = ''
                return
        
        #confirm skip aisle
        if prompt_yes_no(itext('generic.skip.aisle.confirm')):
            for pick in self._picks_lut:
                if pick['status'] == pass_status:
                    if pick['preAisle'] == curr_pre_aisle and pick['aisle'] == curr_aisle:
                        pick['status'] = skip_status
            

            #send update status
            self._update_status(self._pickList[0]['locationID'], '1', skip_status)
            self.next_state = PICK_ASSIGNMENT_CHECK_NEXT_PICK
            self._aisle_direction=''

  
   
   
obj_factory.set_override(PickAssignmentTask, PickAssignmentTask_Custom)