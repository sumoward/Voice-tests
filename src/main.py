import multi_scan_fix #@UnusedImport

from core.VoiceLink import voicelink_startup

from vocollect_http.httpserver import server_startup
from httpserver_receiving import ReceivingVoiceAppHTTPServer


#dummy ODR to get ODR queue working on startup
from common.VoiceLinkLut import VoiceLinkOdr
from vocollect_core.utilities.localization import itext
from vocollect_core.utilities import obj_factory
from vocollect_core import scanning #@UnusedImport
from voice import get_voice_application_property
import voice
dummyODR = obj_factory.get(VoiceLinkOdr, 'dummy')


#import logging #@UnusedImport
# imports for customizations

#import Custom_Core.CoreTaskCustom #@UnusedImport
#import Custom_Core.TakeBreakTaskCustom #@UnusedImport
#import Custom_Selection.SelectionTaskCustom #@UnusedImport
#import Custom_Selection.PickAssignmentTaskCustom #@UnusedImport
#import Custom_Selection.PickPromptMultipleTaskCustom #@UnusedImport
#import Custom_Selection.PickPromptSingleTaskCustom #@UnusedImport
#import Custom_Selection.BeginAssignmentCustom #@UnusedImport
#import Custom_Selection.GetContainerPrintLabelCustom #@UnusedImport
#import Custom_Selection.OpenContainerCustom #@UnusedImport
#import Custom_Selection.SelectionPrintTaskCustom #@UnusedImport
#import Custom_Selection.NewContainerCustom #@UnusedImport
import logging #@UnresolvedImport

#logging.basicConfig(level=logging.DEBUG)
#logging.debug('**Main') 

def main():
    itext('')
    #logging.debug('--main')
    
    
    # Enabling triggered scanning
    use_trigger_scan_vocab = get_voice_application_property('UseTriggerScanVocab')
     
    voice.log_message("Use Trigger scan vocab value is : "+use_trigger_scan_vocab)
    if use_trigger_scan_vocab == 'true':
        trigger_scan_timeout = int(get_voice_application_property('TriggerScanTimeout'))
        scanning.set_trigger_vocab('VLINK_SCAN_VOCAB')
        scanning.set_trigger_timeout(trigger_scan_timeout)
        
    server_startup(ReceivingVoiceAppHTTPServer)
    voicelink_startup()
    
    