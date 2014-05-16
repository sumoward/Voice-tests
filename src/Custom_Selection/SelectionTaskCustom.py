from vocollect_core.task.task import TaskBase

from vocollect_core.dialog.functions import prompt_ready, prompt_only, prompt_words
from vocollect_core import itext, obj_factory
from common.VoiceLinkLut import VoiceLinkLut

from common.RegionSelectionTasks import SingleRegionTask, GET_VALID_REGIONS
from selection.SelectionLuts import Assignments, Containers, Picks, RegionConfig, ValidRegions
from selection.SelectionLuts import IN_PROGRESS_ANOTHER_FUNCTION, IN_PROGRESS_SPECIFIC_REGION
from selection.SelectionPrint import SelectionPrintTask
from Globals import change_function #@UnresolvedImport
from core.SharedConstants import CORE_TASK_NAME, REQUEST_FUNCTIONS
from selection.SharedConstants import SELECTION_TASK_NAME, REGIONS,\
    VALIDATE_REGION, GET_ASSIGNMENT, CHECK_ASSIGNMENT, BEGIN_ASSIGNMENT,\
    PICK_ASSIGNMENT, PICK_REMAINING, PRINT_LABEL, DELIVER_ASSIGNMENT,\
    COMPLETE_ASSIGNMENT, PROMPT_ASSIGNMENT_COMPLETE
from vocollect_core.utilities import class_factory
from selection.SelectionTask import SelectionTask, SelectionRegionTask
from selection.GetAssignment import GetAssignmentAuto, GetAssignmentManual
from selection.SelectionVocabulary import SelectionVocabulary
from selection.PickAssignment import PickAssignmentTask
from selection.BeginAssignment import BeginAssignment
from selection.DeliverAssignment import DeliverAssignmentTask

import logging #@UnresolvedImport
#logging.basicConfig(level=logging.DEBUG)

class SelectionTask_Custom(SelectionTask):
    pass
    logging.debug('**Selection Task')
    ''' Selection task for the VoiceLink system
    
    Steps:
            1. Get region
            2. Validate region
            3. Get Assignment
            4. Check Assignment 
            5. Begin/Initialize Assignment
            6. Pick Assignment
            7. Pick Remaining
            8. print label
            9. Deliver Assignment
            10. Complete Assignment
            
     Parameters
            function - 3 - normal assignment, 4 - chase assignment, 6 - Both
            taskRunner (Default = None) - Task runner object
            callingTask (Default = None) - Calling task (should be a pick prompt task)
    
    '''

    #-------------------------------------------------------------------------
    def __init__(self, function, taskRunner = None, callingTask = None):
        #EXAMPLE: How to call super init method (or any super method)
        super(SelectionTask, self).__init__(taskRunner, callingTask)
        
        #Set task name
        self.name = SELECTION_TASK_NAME

        self.function = function
        self.dynamic_vocab = obj_factory.get(SelectionVocabulary, taskRunner)
        
        #LUT Definitions
        self._valid_regions_lut = obj_factory.get(ValidRegions, 'prTaskLUTRegionPermissionsForWorkType')
        self._region_config_lut = obj_factory.get(RegionConfig, 'prTaskLUTPickingRegion')
        self._assignment_lut = obj_factory.get(Assignments, 'prTaskLUTGetAssignment', self)
        self._picks_lut = obj_factory.get(Picks, 'prTaskLUTGetPicks')
        self._container_lut = obj_factory.get(Containers, 'prTaskLUTContainer')
        self._stop_assignment_lut = obj_factory.get(VoiceLinkLut, 'prTaskLUTStopAssignment')
        self._pass_assignment_lut = obj_factory.get(VoiceLinkLut, 'prTaskLUTPassAssignment')

        #Class properties
        self._region_selected = False
        self._inprogress_work = False
        self._assignment_iterator = None
        self._assignment_complete_prompt_key = None

        self.pick_only = False
        self._current_region_rec = None
        
        self._pick_assignment_task = obj_factory.get(PickAssignmentTask,
                                                       taskRunner, self)
        
    #----------------------------------------------------------
    def initializeStates(self):
        ''' Initialize States and build LUTs '''
        #get region states
        self.addState(REGIONS, self.regions)
        self.addState(VALIDATE_REGION, self.validate_regions)
        self.addState(GET_ASSIGNMENT, self.get_assignment)
        self.addState(CHECK_ASSIGNMENT, self.check_assignment)
        self.addState(BEGIN_ASSIGNMENT, self.begin_assignment)
        self.addState(PICK_ASSIGNMENT, self.pick_assignment)
        self.addState(PICK_REMAINING, self.pick_remaining)
        self.addState(PRINT_LABEL, self.print_label)
        self.addState(DELIVER_ASSIGNMENT, self.deliver_assignment)
        self.addState(COMPLETE_ASSIGNMENT, self.complete_assignment)
        self.addState(PROMPT_ASSIGNMENT_COMPLETE, self.prompt_assignment_complete)
        
    #----------------------------------------------------------
    def regions(self):
        ''' Run single region selection '''
        logging.debug('--run single region selection in Selection task')
        self.dynamic_vocab.clear()
        self.launch(obj_factory.get(SelectionRegionTask,
                                      self.taskRunner, self))

    #----------------------------------------------------------
    def validate_regions(self):
        logging.debug('--Validate region in Selection task')
        ''' Validates a valid regions was received '''
        #check for valid regions, and that error code 3 
        #was not returned in either LUT
        self.set_sign_off_allowed(True)
        valid = False
        error_code = 0
        for region in self._valid_regions_lut:
            if region['errorCode'] == IN_PROGRESS_ANOTHER_FUNCTION:
                error_code = IN_PROGRESS_ANOTHER_FUNCTION
            if region['number'] >= 0:
                valid = True
        
        if valid and error_code == 0:
            for region in self._region_config_lut:
                if region['errorCode'] == IN_PROGRESS_ANOTHER_FUNCTION:
                    error_code = IN_PROGRESS_ANOTHER_FUNCTION

        #check if valid or not
        if error_code == IN_PROGRESS_ANOTHER_FUNCTION:
            self.return_to(CORE_TASK_NAME, REQUEST_FUNCTIONS)
        elif not valid:
            self.next_state = ''
            prompt_only(itext('generic.regionNotAuth.prompt'))
        else:
            self._region_selected = True
            if self._valid_regions_lut[0]['errorCode'] == IN_PROGRESS_SPECIFIC_REGION:
                self._inprogress_work = True
                prompt_only(itext('selection.getting.in-progress.work'))
            else:
                is_auto_issaunce = self._region_config_lut[0]['autoAssign'] == '1'
                max_work_ids = self._region_config_lut[0]['maxNumberWordID']
                if (is_auto_issaunce and max_work_ids == 1):
#                    result = prompt_ready(itext('selection.start.picking'), False,
#                                                 {'change function' : False,
#                                                  'change region' : False}) 
                    #added by Brian
                    result = prompt_only('DaleFarm picking')

                    if result == 'change function':
                        change_function()
                        self.next_state = VALIDATE_REGION 
                    elif result == 'change region':
                        self.change_region()
                        self.next_state = VALIDATE_REGION 
    #----------------------------------------------------------
    def get_assignment(self):
        logging.debug('--Get assignment in selection task')
        ''' Check type of assignment issuance for 
        region and launch get assignment task '''
        self.set_sign_off_allowed(True)

        if not self.pick_only:
            self.dynamic_vocab.clear()
        
        #check if we should reset current region config record
        #Do not set it if last error was 2 (no assignment for region record),
        #   in this case we want to keep it where it is at
        #Do not set it if only getting pick, this means we are still getting
        #   picks for the current assignment (pick by pick, of go back pass)
        if self._assignment_lut.last_error != 2 and not self.pick_only:
            self._region_config_lut.reset_current() 
        
        current_region = self._region_config_lut.get_current_region_record()
        #Auto issuance single assignment
        if current_region['autoAssign'] == '1':
            self.launch(obj_factory.get(GetAssignmentAuto,
                                          self._region_config_lut,
                                          self._assignment_lut,
                                          self._picks_lut,
                                          self.pick_only,
                                          self.taskRunner, self))
        else:
            self.launch(obj_factory.get(GetAssignmentManual,
                                          self._region_config_lut,
                                          self._assignment_lut,
                                          self._picks_lut,
                                          self.pick_only,
                                          self.taskRunner, self))

    #----------------------------------------------------------
    def check_assignment(self):
        logging.debug('--Check assignment in Selection task' )
        ''' checks assignment for error code of 2 (no assignments available) '''
        if  self._assignment_lut.last_error == 2:
            if self._region_config_lut.has_another_region_record():
                self._region_config_lut.next_region_record()
            else:
                self._region_config_lut.reset_current()
                result = prompt_ready(itext('generic.continue.prompt', 
                                            self._assignment_lut[0]['errorMessage']),
                                      False,
                                      {'change function' : False,
                                       'change region' : False}) 
                if result == 'change function':
                    change_function()
                    self.next_state = CHECK_ASSIGNMENT
                elif result == 'change region':
                    self.change_region()
                    self.next_state = CHECK_ASSIGNMENT

            self.next_state = GET_ASSIGNMENT
        else:
            self._current_region_rec = None
            #search for a region record that matches assignment type
            for region in self._region_config_lut:
                if ((region['assignmentType'] == 2 and self._assignment_lut[0]['isChase'] == '1')
                    or (region['assignmentType'] == 1 and self._assignment_lut[0]['isChase'] == '0')):
                    self._current_region_rec = region
                    
            if self._current_region_rec is None:
                prompt_words(itext('selection.assignment.notmatch.region'),
                             False,
                             {'sign off':False})
                self.sign_off()
                
    #----------------------------------------------------------
    def begin_assignment(self):
        logging.debug('--Begin assignment in Selection task')
        ''' Perform begin assignment prompts '''
        #Check if any picks returned
        self.set_sign_off_allowed(self._current_region_rec['signOffAllowed'])
        
        no_picks = True
        for record in self._picks_lut:
            if record['status'] != '':
                no_picks = False
                break
            
        if no_picks:
            self.next_state = PRINT_LABEL
        else:
            if not self.pick_only:
                self.dynamic_vocab.new_assignment(self._current_region_rec, 
                                                  self._assignment_lut, 
                                                  self._picks_lut,
                                                  self._container_lut)

                self.launch(obj_factory.get(BeginAssignment,
                                              self._current_region_rec, 
                                              self._assignment_lut,
                                              self._picks_lut, 
                                              self._container_lut,
                                              self.taskRunner, self))
            elif self._current_region_rec['goBackForShorts'] != 0 and not self._current_region_rec['pickByPick']:
                if self._picks_lut.has_picks_with_status('S'):
                    prompt_only(itext('selection.pick.prompt.picking.skips.shorts'))
                else:
                    prompt_only(itext('selection.pick.prompt.picking.shorts'))
               
    #----------------------------------------------------------
    def pick_assignment(self):
        ''' perform pick assignment'''
        logging.debug('--Pick assignment in Selection task ')
        self._assignment_iterator = None
        self._pick_assignment_task.configure(self._current_region_rec,
                                             self._assignment_lut,
                                             self._picks_lut,
                                             self._container_lut,
                                             self.pick_only)
        #logging.debug(self._pick_assignment_task)
        self.launch(self._pick_assignment_task)
        
        
    #----------------------------------------------------------
    def pick_remaining(self):
        logging.debug('--Pick remaining in Selection task')
        if self._current_region_rec['pickByPick']:
            logging.debug('--pickbypick')
            self.pick_only = True
            self.next_state = GET_ASSIGNMENT
        elif self._current_region_rec['goBackForShorts'] != 0 and self._picks_lut.has_any_shorts() and not self.pick_only:
            prompt_only(itext('selection.pick.prompt.shorts.reported'))
            if self._picks_lut.has_any_shorts() and self._picks_lut.has_picks_with_status('S'):
                prompt_only(itext('selection.pick.prompt.goback.for.shorts.skips'))
            elif self._picks_lut.has_any_shorts():
                prompt_only(itext('selection.pick.prompt.goback.for.shorts'))
            elif self._picks_lut.has_picks_with_status('S'):
                prompt_only(itext('selection.pick.prompt.goback.for.skips'))
               
            self.pick_only = True
            self.next_state = GET_ASSIGNMENT            
                
    #----------------------------------------------------------                
    def print_label(self):
        logging.debug('--Print label in selection custom')
        
        #if in pick by pick mode prompt picking complete
        if self._current_region_rec['pickByPick']:
            prompt_only(itext('selection.pick.assignment.picking.complete'))        
      
        if self._current_region_rec['printLabels']== '2':
            self.launch(obj_factory.get(SelectionPrintTask,
                                          self._current_region_rec, 
                                          self._assignment_lut[0],  
                                          None, 
                                          0, 
                                          self.taskRunner, self))                         
        
    #----------------------------------------------------------
    def deliver_assignment(self):
        logging.debug('--Deliver assignment in Selection task')
        '''Deliver assignment'''
        self.pick_only = False
        #check target containers, if deliver at close and target container then do not deliver
        if self._current_region_rec['delContWhenClosed'] == "1" and self._picks_lut[0]['targetContainer'] > 0:
            return
        
        assignment = None
        
        try:
            if self._assignment_iterator == None:
                self._assignment_iterator = iter(self._assignment_lut)
            
            assignment = next(self._assignment_iterator) 
        
            if (self.dynamic_vocab._pass_inprogress 
                and assignment['passAssignment'] == '1'):
                self.next_state = DELIVER_ASSIGNMENT
            elif (self._current_region_rec['delivery'] == '1' 
                  or self._current_region_rec['delivery'] == '0'):
                self.launch(obj_factory.get(DeliverAssignmentTask,
                                              self._current_region_rec,
                                              assignment,
                                              self._assignment_lut.has_multiple_assignments(),
                                              self.taskRunner, self), 
                            DELIVER_ASSIGNMENT)
        except StopIteration:
            pass
                
    #----------------------------------------------------------
    def complete_assignment(self):
        '''Complete assignment'''
        logging.debug('--Complete assignment in Selection task')
        #check if any passed assignments
        passed = False
        self.set_sign_off_allowed(True)
        
        for assignment in self._assignment_lut:
            if assignment['passAssignment'] == '1' and self.dynamic_vocab._pass_inprogress:
                passed = True
                        
        # Send LUT telling server the assignment is complete.
        self.dynamic_vocab.clear()
        result = 0
        if passed:
            result = self._pass_assignment_lut.do_transmit(self._assignment_lut[0]['groupID'])
        else:
            result = self._stop_assignment_lut.do_transmit(self._assignment_lut[0]['groupID'])
            
        if result == 2:
            # Special case return code tells the operator to switch regions
            self.next_state = REGIONS
        elif result < 0 or result > 0:
            # Failure to send LUT, retry this state
            self.next_state = COMPLETE_ASSIGNMENT
        else:
            if passed:
                self._assignment_complete_prompt_key = 'selection.pass.assignment.confirm'
            else:
                self._assignment_complete_prompt_key = 'selection.complete.assignment.confirm'

            self.dynamic_vocab.next_pick([])   
            

    
    #----------------------------------------------------------
    def prompt_assignment_complete(self):
        logging.debug('--Prompt_assignment_complete in Selection task')
        # Successful LUT transmission, prompt for next assignment
        result = prompt_ready(itext(self._assignment_complete_prompt_key), True,
                              {'change function' : False,
                               'change region' : False}) 
        if result == 'change function':
            change_function()
            self.next_state = PROMPT_ASSIGNMENT_COMPLETE
        elif result == 'change region':
            self.change_region()
            self.next_state = PROMPT_ASSIGNMENT_COMPLETE
        else:        
            self.next_state = GET_ASSIGNMENT


  
obj_factory.set_override(SelectionTask, SelectionTask_Custom)
#obj_factory.set_override(SelectionRegionTask, SelectionRegionTask_Custom)

