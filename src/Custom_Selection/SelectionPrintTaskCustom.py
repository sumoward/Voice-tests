from selection.SelectionPrint import SelectionPrintTask
from vocollect_core.utilities import obj_factory

from common.VoiceLinkLut import VoiceLinkLut
from vocollect_core import itext, class_factory, obj_factory
from vocollect_core.dialog.functions import prompt_yes_no, prompt_only, prompt_alpha_numeric
from core.Print import PrintTask
from selection.SharedConstants import SELECTION_PRINT_TASK_NAME,\
    SELECTION_TASK_NAME, ENTER_PRINTER, CONFIRM_PRINTER, PRINT_LABELS,\
    REPRINT_LABELS

import logging #@UnresolvedImport
#logging.basicConfig(level=logging.DEBUG)


class SelectionPrintTask_Custom(SelectionPrintTask):
    pass
    logging.debug('**SelectionPrintTask_Custom')
    ''' Selection print task
    
     Steps:
            1. Enter Printer Number
            2. Confirm Printer Number
            3. Print
            4. reprint labels

     Parameters
            region - region operator is picking in 
            assignment_lut - assignments currently working on
            picks - pick list for specific location
            container_lut - current list of containers
            taskRunner (Default = None) - Task runner object
            callingTask (Default = None) - Calling task (should be a pick prompt task)
        
    '''
    
    #-------------------------------------------------------------------------
    def __init__(self, 
                 region,  
                 assignment, 
                 container_lut, 
                 reprint_label,
                 taskRunner = None, 
                 callingTask = None):
        super(SelectionPrintTask, self).__init__(taskRunner, callingTask)

        #Set task name
        self.name = SELECTION_PRINT_TASK_NAME

        #Luts and lut records
        self._assignment = assignment
        self._region = region
        self._reprint_label = reprint_label
        self._container_lut = container_lut
     
        self.task = self.taskRunner.findTask(SELECTION_TASK_NAME)
        if self.task is None:
            self.task = self.callingTask
        self._set_variables()
            
    def _set_variables(self):            
        self.operation = 1
        self.is_chase = False
        
        if self._assignment is None:
            return
        
        if self._assignment['isChase'] == '1':
            self.is_chase = True
            self.operation = 0
        
        
    #-------------------------------------------------------------------------
    def initializeStates(self):
        ''' Initialize States and build LUTs '''
        
        #get printer states
        self.addState(ENTER_PRINTER, self.enter_printer)
        #comment out the confirm printer
        #self.addState(CONFIRM_PRINTER, self.confirm_printer)
        self.addState(PRINT_LABELS, self.print_label)
        self.addState(REPRINT_LABELS, self.reprint_labels)
        
        self._print_lut = obj_factory.get(VoiceLinkLut, 'prTaskLUTPrint')
        self.task = self.taskRunner.findTask(self.name)
        self.dynamic_vocab = None #do not want the selection dynamic vocab
        
    #-------------------------------------------------------------------------
    def print_label(self):
        ''' print labels'''  
        logging.debug('--print_label')  
        #if reprint labels is not set 
        if not self._reprint_label:
            assignment_id = self._assignment['assignmentID']
            if self._region['containerType'] == 0 and self._assignment.parent.has_multiple_assignments():
                assignment_id= ''
                
            result = self._print_lut.do_transmit(self._assignment['groupID'], assignment_id,
                                             self.operation, '', self.task.printer_number, self._reprint_label)
        
            if result < 0:
                self.next_state = PRINT_LABELS
            elif result > 0:
                self.next_state = ENTER_PRINTER
            else:
                self.next_state = ''
        else:
            self.next_state = REPRINT_LABELS    
            
    #----------------------------------------------------------          
    def reprint_labels(self):
        ''' Reprint labels command is used by the operator'''
        logging.debug('--reprint_label') 
        #is this chase assignment or container type is 0
        if self.is_chase or self._region['containerType'] == 0:
            assignment_id = self._assignment['assignmentID']
            if self._assignment.parent.has_multiple_assignments():
                assignment_id = ''
            self._print_lut.do_transmit(self._assignment['groupID'], assignment_id,
                                             self.operation, '', self.task.printer_number, self._reprint_label)
        else:
            # is regions container type setting - pick to containers
            container, container_scanned = prompt_alpha_numeric(itext('selection.put.prompt.for.container'), 
                                                           itext('selection.new.container.prompt.for.container.help'), 
                                                           self._region['spokenContainerLen'], self._region['spokenContainerLen'],
                                                           confirm=True,scan=True, additional_vocab={'all':False, 'no more':False})
            #if all is spoken system container id null operation 1  
            if container == 'no more':
                self.next_state = ''
            elif container == 'all':
                logging.debug('--all selected by user') 
                if prompt_yes_no(itext('selection.reprint.labels.all.correct')):
                    self._print_lut.do_transmit(self._assignment['groupID'], '',
                                                self.operation, '', self.task.printer_number, self._reprint_label) 
                else:
                    self.next_state = REPRINT_LABELS
            else:    
                valid_container = self._container_lut._get_container(container, container_scanned)
                logging.debug('--is valid container ? ') 
                #Verify if the container is a valid container or is already closed
                if not valid_container:
                    prompt_only(itext('selection.reprint.label.container.not.valid', container))
                    self.next_state = REPRINT_LABELS
                else:
                    system_container_id = self._container_lut._get_container(container, container_scanned)
                    #system container id operation 1
                    self._print_lut.do_transmit(self._assignment['groupID'], system_container_id['assignmentID'],
                                             self.operation, system_container_id['systemContainerID'], self.task.printer_number, self._reprint_label) 
                    
   
    




obj_factory.set_override(SelectionPrintTask, SelectionPrintTask_Custom)