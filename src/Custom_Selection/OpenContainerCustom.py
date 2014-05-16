from selection.OpenContainer import OpenContainer
from vocollect_core.utilities import obj_factory
from vocollect_core.task.task import TaskBase

from vocollect_core.dialog.functions import prompt_ready, prompt_alpha_numeric 
from vocollect_core import itext, obj_factory, class_factory
from selection.SelectionPrint import SelectionPrintTask
from selection.SharedConstants import OPEN_CONTAINER_TASK_NAME,\
    OPEN_CONTAINER_OPEN

import logging #@UnresolvedImport
#logging.basicConfig(level=logging.DEBUG)

class OpenContainer_Custom(OpenContainer):
    pass
    logging.debug('**Open Container Custom')
    '''Process open container
    
     Steps:
            1. Open container
          
     Parameters
            region - region operator is picking in 
            assignment - assignment currently working on
            picks_lut - pick list
            container_lut - current list of containers
            multiple_assignments - is operator working on multiple assignments or not
            taskRunner (Default = None) - Task runner object
            callingTask (Default = None) - Calling task (should be a pick prompt task)
    '''
    
    #----------------------------------------------------------
    def __init__(self, 
                 region,  
                 assignment, 
                 picks_lut, 
                 container_lut,
                 multiple_assignments,
                 taskRunner = None, callingTask = None):
        super(OpenContainer, self).__init__(taskRunner, callingTask)
        
        #Set task name
        self.name = OPEN_CONTAINER_TASK_NAME

        self._region = region
        self._assignment = assignment
        self._container_lut = container_lut
        self._multiple_assignments = multiple_assignments
        self._picks = picks_lut
        self._position = ''
        self._set_variables()
        
    #----------------------------------------------------------
    def _set_variables(self):
        if self._multiple_assignments == True:
            self._position = self._assignment['position']
       
    #----------------------------------------------------------
    def initializeStates(self):
        ''' Initialize States and build LUTs '''
        self.addState(OPEN_CONTAINER_OPEN, self.open_container)
           
    #----------------------------------------------------------
    def open_container(self):
        logging.debug('--open container')
        container=''
        
        if self._position == '':
            prompt = itext('selection.new.container.prompt.for.container.id')
        else:
            prompt = itext('selection.new.container.prompt.for.container', self._position)
           
        if self._region['promptForContainer'] == 1:
            result = prompt_alpha_numeric(prompt, 
                                          itext('selection.new.container.prompt.for.container.help'), 
                                          confirm=True,scan=True)
            container = result[0]
            
        result = -1
        if self._picks[0]['targetContainer'] == 0:
            target_container = ''
        else:
            target_container = self._picks[0]['targetContainer']
            
        while result < 0:
            result = self._container_lut.do_transmit(self._assignment['groupID'], 
                                                     self._assignment['assignmentID'], target_container, '', container, 2 , '')
        
        if result > 0:
            self.next_state = OPEN_CONTAINER_OPEN
            
        if result == 0:
            if self._region['promptForContainer'] != 1:
                if self._position == '':
                    prompt_last = itext('selection.new.container.prompt.open.last', self._container_lut[0]['spokenValidation'])
                    if self._picks[0]['targetContainer'] != 0:
                        self._assignment['activeTargetContainer'] = self._container_lut[0]['targetConatiner']
                else:
                    containers = self._container_lut.get_open_containers(self._assignment['assignmentID'])
                    if len(containers) == 0:
                        containers = self._container_lut.get_closed_containers(self._assignment['assignmentID'])
                    if len(containers) > 0:    
                        prompt_last = itext('selection.new.container.prompt.open.last.multiple', 
                                          containers[0]['spokenValidation'], 
                                             self._position)
                    else:
                        prompt_last = itext('selection.new.container.no.containers.returned')
                        
                prompt_ready(prompt_last)
            
            if self._region['printLabels'] == '1':
                if  self._container_lut[0]['printed']  == 0:
                    self._print_label()
        
    #----------------------------------------------------------      
    def _print_label(self):
        '''Printing label'''
        logging.debug('print in  open container')
        self.launch(obj_factory.get(SelectionPrintTask,
                                      self._region, 
                                      self._assignment, 
                                      self._container_lut,  
                                      0, 
                                      self.taskRunner, self))

    
    
    
    
    
    
    
obj_factory.set_override(OpenContainer, OpenContainer_Custom)