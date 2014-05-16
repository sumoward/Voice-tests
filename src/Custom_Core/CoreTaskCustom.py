from vocollect_core.utilities import obj_factory
from core.CoreTask import CoreTask, ConfigurationLut, SignOffLut
from vocollect_core.utilities.localization import itext
from core.SharedConstants import REQUEST_CONFIG
from voice import globalwords as gw
from common.VoiceLinkLut import VoiceLinkLut, VoiceLinkLutOdr

from vocollect_core.task.task import TaskBase

from vocollect_core.dialog.functions import prompt_only, prompt_ready, prompt_digits, prompt_list_lut_auth, prompt_yes_no, prompt_words
from vocollect_core import itext, obj_factory
from vocollect_core.utilities import class_factory
from common.VoiceLinkLut import VoiceLinkLut
from voice import globalwords as gw
from voice import getenv
from voice import get_voice_application_property

from httpserver_receiving import DEFAULT_PAGE
from vocollect_http.httpserver import set_display_page

#Tasks
from core.VehicleTask import VehicleTask
from core.TakeBreakTask import TakeBreakTask
from backstocking.BackStockingTask import BackstockingTask
from lineloading.LineLoadingTask import LineLoadingTask
from loading.LoadingTask import LoadingTask
from forkapps.PutawayTask import PutawayTask
from forkapps.ReplenishmentTask import ReplenishmentTask
from puttostore.PutToStoreTask import PutToStoreTask
from selection.SelectionTask import SelectionTask
from cyclecounting.CycleCountingTask import CycleCountingTask
from receiving.ReceivingTask import ReceivingTask
from core.SharedConstants import CORE_TASK_NAME, REQUEST_CONFIG, REQUEST_BREAKS,\
    GET_WELCOME, REQUEST_SIGNON, REQUEST_VEHICLES, REQUEST_FUNCTIONS,\
    EXECUTE_FUNCTIONS

import logging #@UnresolvedImport
#comment this next line to turn off debuging output
logging.basicConfig(level=logging.DEBUG)


#--------------------------------------------------------------
class CoreTask_Custom(CoreTask):
    logging.debug('**Custom Core ')
              
#----------------------------------------------------------
    def vehicles(self):
        ''' Run vehicle types task, return to request function '''
        #EXAMPLE: Launch task from another task using launch method
        #         when calling this way, user must set next state
        #         before calling launch, otherwise after launched task
        #         completes the state is repeated (execute_function is 
        #         example of state being repeated)
        #{brian edit] do not call the vehicle check state
        pass
        logging.debug('--Vehicle function1')
        #self.launch(obj_factory.get(VehicleTask, self.taskRunner))      
        
#    def request_functions(self):
#        ''' request function from host '''
#        logging.debug('--Request function')
#        self.sign_off_allowed = True
##{brian edit] do not ask for functions from
##        if not self.xmit_functions():
#        self.next_state = EXECUTE_FUNCTIONS
    
    #----------------------------------------------------------
#    def execute_function(self):
#        ''' prompt for function and execute it '''
#        logging.debug('--Execute function here')
#        self.sign_off_allowed = True
#        self.function = 3
##        logging.debug('***')
##        logging.debug('self.function is ', obj_factory.get(SelectionTask, self.function, self.taskRunner, self), 
##                        EXECUTE_FUNCTIONS)
##        logging.debug('***')
#        self.launch(obj_factory.get(SelectionTask, self.function, self.taskRunner, self), 
#                        EXECUTE_FUNCTIONS)
          
#----------------------------------------------------------
    def request_functions(self):
        ''' request function from host '''
        self.sign_off_allowed = True
        if not self.xmit_functions():
            self.next_state = REQUEST_FUNCTIONS
                
    #----------------------------------------------------------
    def execute_function(self):
        ''' prompt for function and execute it '''
        self.sign_off_allowed = True
        
        #if only 1 record returned then automatically select that function
        self.function = None
        if len(self._functions_lut) == 1:
            self.function = self._functions_lut[0]['number']
            prompt_only(self._functions_lut[0]['description'])
        #else prompt user to select function
        else:
            self.function = prompt_list_lut_auth(self._functions_lut, 
                                            'number', 'description',  
                                            itext('core.function.prompt'), 
                                            itext('core.function.help'))
        
        self.function = str(self.function)
        #Execute selected function
        if self.function == '1': #PutAway
            self.launch(obj_factory.get(PutawayTask, self.taskRunner, self), 
                        EXECUTE_FUNCTIONS)
        elif self.function == '2': #Replenishment
            self.launch(obj_factory.get(ReplenishmentTask, self.taskRunner, self), 
                        EXECUTE_FUNCTIONS)
        elif self.function in ['3', '4', '6']: #Selection
            self.launch(obj_factory.get(SelectionTask, self.function, self.taskRunner, self), 
                        EXECUTE_FUNCTIONS)
        elif self.function == '7': #Line Loading
            self.launch(obj_factory.get(LineLoadingTask, self.taskRunner, self), 
                        EXECUTE_FUNCTIONS)
        elif self.function == '8': #Put to store
            self.launch(obj_factory.get(PutToStoreTask, self.taskRunner, self), 
                        EXECUTE_FUNCTIONS)
        elif self.function == '9': #Cycle Counting
            self.launch(obj_factory.get(CycleCountingTask, self.taskRunner, self), 
                        EXECUTE_FUNCTIONS)
        elif self.function == '10': #Loading
            self.launch(obj_factory.get(LoadingTask, self.taskRunner, self), 
                        EXECUTE_FUNCTIONS)
        elif self.function == '11': #Back Stocking
            self.launch(obj_factory.get(BackstockingTask, self.taskRunner, self), 
                        EXECUTE_FUNCTIONS)
        elif self.function == '12': #Receiving
            self.launch(obj_factory.get(ReceivingTask, self.taskRunner, self), 
                        EXECUTE_FUNCTIONS)
        else: #Function specified not implemented
            prompt_ready(itext('core.function.notimplemented', str(self.function)))
            self.next_state = REQUEST_FUNCTIONS 
            
    #----------------------------------------------------------

##Replace original class with new custom class
obj_factory.set_override(CoreTask, CoreTask_Custom)
