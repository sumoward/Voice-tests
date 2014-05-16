from core.TakeBreakTask import TakeBreakTask
from vocollect_core.utilities import obj_factory

from vocollect_core.task.task import TaskBase
from vocollect_core.dialog.functions import prompt_ready, prompt_list_lut, prompt_digits_required
from vocollect_core import itext, class_factory
from common.VoiceLinkLut import VoiceLinkOdr

from voice import globalwords as gw
from pending_odrs import wait_for_pending_odrs
from core.SharedConstants import TAKE_A_BREAK_TASK_NAME, SELECT_BREAK,\
    TRANSMIT_START_BREAK, ENTER_PASSWORD, TRANSMIT_STOP_BREAK
from vocollect_core.utilities import obj_factory



import logging #@UnresolvedImport
#logging.basicConfig(level=logging.DEBUG)

class TakeBreakTask_Custom(TakeBreakTask):
    pass
    logging.debug('**TakeBreakTask')
    ''' Take a break task
    
    Steps:
            1. Select Break
            2. Transmit start of break
            3. Enter password
            4. Transmit stop of break 
            
    '''

    #----------------------------------------------------------
    def __init__(self, breaks_lut, password, 
                 taskRunner = None, callingTask = None):
        super().__init__(taskRunner, callingTask)

        self.name = TAKE_A_BREAK_TASK_NAME

        self._breaks_lut = breaks_lut
        self.password = password
        self.breaktype = ''
        self._break_odr = obj_factory.get(VoiceLinkOdr, 'prTaskODRCoreSendBreakInfo')
    
    #----------------------------------------------------------
    def initializeStates(self):
        ''' Initialize States '''
        
        #set states for take a break
        self.addState(SELECT_BREAK, self.selectBreak)
        self.addState(TRANSMIT_START_BREAK, self.startBreak)
        self.addState(ENTER_PASSWORD, self.enterPassword)
        self.addState(TRANSMIT_STOP_BREAK, self.stopBreak)

    #----------------------------------------------------------
    def selectBreak(self):
        logging.debug('--selectbreak')
        ''' select break type '''
        self.breakType = prompt_list_lut(self._breaks_lut, 
                                         'type', 'description',  
                                         itext('core.take.a.break.type'),
                                         itext('core.take.a.break.type.help'))
        
    
    #----------------------------------------------------------
    def startBreak(self):
        logging.debug('--startbreak')
        ''' transmit up start of break '''
        self._break_odr.do_transmit(self.breakType, 0, self._get_description())
        wait_for_pending_odrs('VoiceLink')   
    
    #----------------------------------------------------------
    def enterPassword(self):
        logging.debug('--enter password')
        ''' enter password to end break '''
        prompt_ready(itext('core.take.a.break.continue.work'))
        prompt_digits_required(itext('core.password.prompt'), 
                               itext('core.password.help'),
                               [self.password])

    #----------------------------------------------------------
    def stopBreak(self):
        logging.debug('--stop break')
        ''' transmit up end of break '''
        self._break_odr.do_transmit(self.breakType, 1, self._get_description())
        wait_for_pending_odrs('VoiceLink')   
        gw.words['take a break'].enabled = True  
        
    # Gets the description to append to the ODR
    def _get_description(self):
        logging.debug('--get break description')
        ''' get break type description '''
        description = ''
        for breaktype in self._breaks_lut:
            if(str(breaktype['type']) == self.breakType):
                description = breaktype['description']
                
        return description

    
    
    
    
    
obj_factory.set_override(TakeBreakTask, TakeBreakTask_Custom)