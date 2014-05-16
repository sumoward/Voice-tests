from selection.NewContainer import NewContainer
from vocollect_core.utilities import obj_factory

from vocollect_core.task.task import TaskBase

from vocollect_core.dialog.functions import prompt_yes_no, prompt_only 
from vocollect_core import itext, obj_factory, class_factory
from selection.OpenContainer import OpenContainer
from selection.CloseContainer import CloseContainer
from selection.SharedConstants import NEW_CONTAINER_TASK_NAME,\
    CONFIRM_NEW_CONTAINER, CLOSE_CONTAINER, OPEN_CONTAINER,\
    NEW_RETURN_AFTER_DELIVERY, PICK_ASSIGNMENT_TASK_NAME,\
    PICK_ASSIGNMENT_CHECK_NEXT_PICK, PICK_PROMPT_TASK_NAME, SLOT_VERIFICATION
    
import logging #@UnresolvedImport

#logging.basicConfig(level=logging.DEBUG)

class NewContainer_Custom(NewContainer):
    pass
    logging.debug('**New Container Custom')
    
    '''process new container
    
     Steps:
        1) Confirm close container
        2) Close Container
        3) Open Container
        4) Check Return after Delivery
          
     Parameters
        region - region operator is picking in 
        assignment - assignment currently working on
        picks_lut - the current list of picks currently be worked on
        container_lut - the current list of containers
        multiple_assignments - is operator working on multiple assignments or not
        current_container - container for the current assignment
        taskRunner (Default = None) - Task runner object
        callingTask (Default = None) - Calling task (should be a pick prompt task)'''
    
    #----------------------------------------------------------
    def __init__(self, 
                 region, 
                 assignment, 
                 picks_lut, 
                 container_lut,
                 multiple_assignments,
                 current_container,
                 taskRunner = None, 
                 callingTask = None):
        super(NewContainer, self).__init__(taskRunner, callingTask)

        #Set task name
        self.name = NEW_CONTAINER_TASK_NAME

        self._region = region
        self._assignment = assignment
        self._picks = picks_lut
        self._container_lut = container_lut
        self._multiple_assignments = multiple_assignments
        self._container = current_container
        self._container_closed = False
        self.dynamic_vocab = None
        
    #----------------------------------------------------------
    def initializeStates(self):
        ''' Initialize States and build LUTs '''
        
        self.addState(CONFIRM_NEW_CONTAINER, self.confirm_new_container)
        self.addState(CLOSE_CONTAINER, self.close_container)
        self.addState(OPEN_CONTAINER, self.open_container)
        self.addState(NEW_RETURN_AFTER_DELIVERY, self.return_after_delivery)
           
    #----------------------------------------------------------
    def confirm_new_container(self):
        logging.debug("--confirm new container")
        ''' confirm new container and close current container if multiple open'''
        if self._picks[0]['targetContainer'] > 0:
            prompt_only(itext('selection.new.container.not.allowed.target.containers'))
            self.next_state = ''
        else:
            logging.debug("--else")
            if prompt_yes_no(itext('selection.new.container.confirm')):
                if self._region['allowMultOpenCont']:
                    #check to see if there are multiple open containers
                    if not self._container_lut.multiple_open_containers(self._assignment['assignmentID']):
                        if not prompt_yes_no(itext('selection.new.container.close.current.container')):
                            
                            self.next_state=OPEN_CONTAINER
                        else:
                            logging.debug("--confirm close prompt?")
                            self.next_state=CLOSE_CONTAINER
                    else:
                        logging.debug("--multiple containers open?")
                        self.next_state = OPEN_CONTAINER
            else:
                self.next_state = ''
          
    #----------------------------------------------------------
    def close_container(self):
        logging.debug("--close container")
        '''close container the current container'''
        close_container_command = False
        self._container_closed = True
        self.launch(obj_factory.get(CloseContainer,
                                      self._region,
                                      self._assignment, 
                                      self._picks,
                                      self._container_lut,
                                      self._multiple_assignments,
                                      close_container_command,
                                      self._container,
                                      self.taskRunner, self))

    #----------------------------------------------------------
    def open_container(self):
        logging.debug('--open_container')
        ''' Launch open container task'''
        self.launch(obj_factory.get(OpenContainer,
                                      self._region,
                                      self._assignment,
                                      self._picks,
                                      self._container_lut,
                                      self._multiple_assignments,
                                      self.taskRunner, self))
        
        
    #----------------------------------------------------------
    def return_after_delivery(self):
        logging.debug('--return_after_delivery')
        ''' return to slot verification if delivered the assignment'''
        if self._region['delivery'] != '2' and self._region['delContWhenClosed']=='1':
            pickTask = self.taskRunner.findTask(PICK_ASSIGNMENT_TASK_NAME)
        
            if pickTask != None:
                pickTask._aisle_direction = ''
                pickTask._pre_aisle_direction = ''
                pickTask._post_aisle_direction = ''
                self.taskRunner.return_to(pickTask.name, 
                                          PICK_ASSIGNMENT_CHECK_NEXT_PICK)
        #else if printing labels when container opened
        #or printing labels when container is close (and actually closed container)
        elif (self._region['printLabels'] == '1' or 
              (self._region['printLabels'] == '2' and self._container_closed)):
            self.task = self.taskRunner.findTask(PICK_PROMPT_TASK_NAME)
    
            if self.task != None:
                self.taskRunner.return_to(self.task.name, 
                                          SLOT_VERIFICATION)

    
    
    
    
obj_factory.set_override(NewContainer, NewContainer_Custom)