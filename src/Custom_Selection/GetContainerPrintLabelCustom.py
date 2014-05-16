from selection.GetContainerPrintLabel import GetContainerPrintLabel
from vocollect_core.task.task import TaskBase

from vocollect_core.dialog.functions import prompt_yes_no, prompt_digits 
from vocollect_core import itext, obj_factory, class_factory

from selection.SelectionPrint import SelectionPrintTask
from selection.SharedConstants import GET_CONTAINER_PRINT_LABEL_TASK_NAME, START,\
    GET_NEXT_ASSIGNMENT, CHECK_PICKS, CHECK_CHASE_ASSIGNMENT,\
    NO_PICK_TO_CONTAINER, PROMPT_FOR_CONTAINER, NO_PRINT_LABEL,\
    PRE_CREATE_CONTAINERS, GET_CONTAINER, NEW_CONTAINER, PRINT, PRINT_RETURN
from selection.OpenContainer import OpenContainer

import logging #@UnresolvedImport
#logging.basicConfig(level=logging.DEBUG)

class GetContainerPrintLabel_Custom(GetContainerPrintLabel):
    pass
    logging.debug('**Get container print label Custom')
    '''Get Container and print label
    
    Steps:
         1. Start
         2. Get next assignment
         3. Check picks
         4. Check chase assignment
         5. Check pick to containers or just printing
         6. Prompt for container
         7. Check if printing labels
         8. Pre Create Containers
         9. Get Container
         10. New Container
         11. Print
         12. Print Return
          
     Parameters
         region - region operator is picking in 
         assignment_lut - assignments currently working on
         picks - the current list of picks currently be worked on
         container_lut - current containers
         taskRunner (Default = None) - Task runner object
         callingTask (Default = None) - Calling task (should be a pick prompt task)'''
            
    #----------------------------------------------------------
    def __init__(self, region, assignment_lut, picks, container_lut,
                 taskRunner = None, callingTask = None):
        
        super(GetContainerPrintLabel, self).__init__(taskRunner, callingTask)

        #Set task name
        self.name = GET_CONTAINER_PRINT_LABEL_TASK_NAME
        
        #Luts and lut records
        self._region = region
        self._picks = picks
        self._assignment_lut = assignment_lut
        self._container_lut = container_lut
        self._set_variables()
        self._assignment = None
        self._print_create = False
          
    #----------------------------------------------------------
    def _set_variables(self):
         
        if len(self._assignment_lut) == 0:
            return
             
        self._assignment_iterator = iter(self._assignment_lut)
         
             
    #----------------------------------------------------------
    def initializeStates(self):
        ''' Initialize States'''

        self.addState(START, self.start)
        self.addState(GET_NEXT_ASSIGNMENT, self.get_next_assignment)
        self.addState(CHECK_PICKS, self.check_picks_to_pick)
        self.addState(CHECK_CHASE_ASSIGNMENT, self.check_chase_assignment)
        self.addState(NO_PICK_TO_CONTAINER, self.not_pick_to_container)
        self.addState(PROMPT_FOR_CONTAINER, self.prompt_for_container)
        self.addState(NO_PRINT_LABEL, self.no_print_label)
        self.addState(PRE_CREATE_CONTAINERS, self.pre_create_containers)
        self.addState(GET_CONTAINER, self.get_container)
        self.addState(NEW_CONTAINER, self.new_container)
        self.addState(PRINT, self.print_label)
        self.addState(PRINT_RETURN, self.print_return)
        
       
    #----------------------------------------------------------    
    def start(self):
        ''' Start with the first assignment'''
        logging.debug('--Start get container')
        if self._region['containerType'] != 0:
            result = -1
           
            while result != 0:   
                result = self._container_lut.do_transmit(self._assignment_lut[0]['groupID'], 
                                                         '', 
                                                         '', 
                                                         '', 
                                                         '', 
                                                         '0' , 
                                                         '' )
                                   
    #----------------------------------------------------------                              
    def get_next_assignment(self):
        ''' get next assignment '''
        logging.debug('--Get next assignement in get container')
        
        #EXAMPLE: How to iterate over a list through different states
        try:
            self._assignment = next(self._assignment_iterator)
            if self._region['containerType'] == 0:
                self.next_state = CHECK_CHASE_ASSIGNMENT
        except:
            self.next_state = ''
  
    #----------------------------------------------------------         
    def check_picks_to_pick(self):
        ''' check if there are any picks to be picked'''
        logging.debug('--picks to pick in get container')
        #checking to see if there are any picks that are not picked
        if self._region['pickByPick']:
            has_picks = self._picks.has_picks(self._assignment, ['N', 'B', ''])
        else:
            has_picks = self._picks.has_picks(self._assignment, ['N', 'B'])
              
        # Verifying if the assignment has any more picks to pick are there any open containers if there
        # are open containers get next assignment else create new container and get next assignment       
        if has_picks:
            has_open_containers = self._container_lut.has_containers(self._assignment, 'O')
            #returned no containers
            if  len(self._container_lut) == 1 and self._container_lut[0]['status'] == '':
                self.next_state = CHECK_CHASE_ASSIGNMENT
            elif  has_open_containers is not True :
                self.next_state = NEW_CONTAINER
            else:
                self.next_state = GET_NEXT_ASSIGNMENT
        else:
            self.next_state = GET_NEXT_ASSIGNMENT      
        
    #----------------------------------------------------------    
    def check_chase_assignment(self):
        #verify if it is a chase assignment and regions print chase labels 
        if self._assignment['isChase'] == '1' and self._region['printChaseLabels'] == '1':
            self.next_state = PRINT
           
    #----------------------------------------------------------          
    def not_pick_to_container(self):
        #regions container type is pick to containers
        if self._region['containerType'] == 0:
            if self._region['printLabels'] == '1':
                # This is a bug in task builder that it prompts to print labels just once 
                # So adding anew state to handle this. In future this state will be PRINT 
                #and new state will be removed.
                self.next_state = PRINT_RETURN
            else:
                self.next_state = GET_NEXT_ASSIGNMENT
                
    #----------------------------------------------------------
    def prompt_for_container(self):
        #go to new container launch a task
        logging.debug('--Prompt for container in get container')
        if self._region['promptForContainer'] != 0:
            self.next_state = NEW_CONTAINER
    
    #----------------------------------------------------------    
    def no_print_label(self):
        #print label not set
        logging.debug('--Print no label in get container')
        if self._region['printLabels'] == '0':
            self.next_state = NEW_CONTAINER
     
    #----------------------------------------------------------          
    def pre_create_containers(self):
        ''' pre-create containers'''
        logging.debug('--Precreate in get container')
        if self._region['printNumLabels'] != '1':
            self.next_state = NEW_CONTAINER
        
    #----------------------------------------------------------    
    def get_container(self):
        ''' Create new container or print label'''
        logging.debug('--Get container in get container')
        if self._picks[0]['targetContainer'] > 0:
            #NOTE - Just a place holder for target containers
            if prompt_yes_no(itext('selection.container.preprint.all.labels',self._picks[0]['idDescription'])):
                result = -1
                while result != 0:
                    result = self._container_lut.do_transmit(self._assignment['groupID'], 
                        self._picks[0]['assignmentID'], '', '', '' , '3', '')
                self.next_state = PRINT
                self._print_create = True
                self._assignment['activeTargetContainer'] = self._container_lut[0]['targetConatiner']
            else:
                    self.next_state = NEW_CONTAINER
        else:
            label = prompt_digits(itext('selection.container.number.of.labels',  self._assignment['idDescription']), 
                                                        itext('selection.container.number.of.labels.help'), 
                                                        confirm = False)
            result = -1
            while result != 0:
                result = self._container_lut.do_transmit(self._assignment['groupID'], 
                           self._picks[0]['assignmentID'], '', '', '', '3', label)
            self._print_create = True
            self.next_state = PRINT
            
    #----------------------------------------------------------    
    def new_container(self):
        ''' create new container'''
        logging.debug('--New container in get container')
         
        self.launch(obj_factory.get(OpenContainer,
                                      self._region,
                                      self._assignment, 
                                      self._picks,
                                      self._container_lut,
                                      len(self._assignment_lut) > 1,
                                      self.taskRunner, self),
                    GET_NEXT_ASSIGNMENT)
   
    #----------------------------------------------------------   
    def print_label(self):
        '''Print label'''
        logging.debug('--Printing label in get container ')
        if  self._print_create == True:
            print('--printing label 1')
            self._print_create = False
            self.launch(obj_factory.get(SelectionPrintTask,
                                          self._region, 
                                          self._assignment, 
                                          self._container_lut, 
                                          0, 
                                          self.taskRunner, self), 
                    NEW_CONTAINER)
        else: 
            logging.debug('--printing label 2')
            self.launch(obj_factory.get(SelectionPrintTask,
                                          self._region, 
                                          self._assignment, 
                                          self._container_lut,  
                                          0,  
                                          self.taskRunner, self), 
                    GET_NEXT_ASSIGNMENT)
            

    #----------------------------------------------------------   
    def print_return(self):
        '''Print label and return'''
        logging.debug('--Print return in get container')
        self.launch(obj_factory.get(SelectionPrintTask,
                                      self._region, 
                                      self._assignment, 
                                      self._container_lut, 
                                      0, 
                                      self.taskRunner, 
                                      self))

    
  
   
   
obj_factory.set_override(GetContainerPrintLabel, GetContainerPrintLabel_Custom)