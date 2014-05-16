from selection.PickPromptSingle import PickPromptSingleTask
from vocollect_core.utilities import obj_factory
from vocollect_core.dialog.functions import prompt_digits, prompt_digits_required , prompt_only,\
    prompt_yes_no

from vocollect_core import itext, class_factory
from selection.PickPrompt import PickPromptTask, SLOT_VERIFICATION, ENTER_QTY,\
    QUANTITY_VERIFICATION, LOT_TRACKING

import logging #@UnresolvedImport
from common.VoiceLinkLut import VoiceLinkLutOdr
#logging.basicConfig(level=logging.DEBUG)

class PickPromptSingleTask_Custom(PickPromptSingleTask):
    pass
    logging.debug('**Single task prompts ')
    '''Pick prompts for regions with single pick prompt defined
     Extends PickPromptTask
     
     Steps:
            1. Slot verification (Overridden)
            2. Enter Quantity (Overridden)
            
            Remaining steps are the same as base
          
     Parameters
             Same as base class
    '''
    
    #----------------------------------------------------------
    def slot_verification(self):
        '''override for Single Prompts''' 
        logging.debug('--Slot_verification in PickPromptSingleTask_Custom')
        
        #if pick prompt type is 1 prompt only slot assuming they are picking just 1pick prompt single
        additional_vocabulary={'short product' : False, 
                               'ready' : False, 
                               'skip slot' : False,
                               'partial' : False}
      
        if self._region['pickPromptType'] == '1' and self._expected_quantity == 1:
            prompt = itext("selection.pick.prompt.single.slot.only", 
                                self._picks[0]["slot"],
                                self._uom, self._description, self._id_description, self._message)
        else:
            prompt = itext("selection.pick.prompt.single.pick.quantity", 
                                self._picks[0]["slot"],
                                self._expected_quantity, self._uom,  self._description, self._id_description, self._message)
   
        result, is_scanned = prompt_digits_required(prompt,
                                                    itext("selection.pick.prompt.checkdigit.help"), 
                                                    [self._picks[0]["checkDigits"], self._pvid], 
                                                    [self._picks[0]["scannedProdID"]], 
                                                    additional_vocabulary,
                                                    self._skip_prompt)
      
        self._skip_prompt = False
        if result == 'short product':
            logging.debug('short product')
            self.next_state = SLOT_VERIFICATION
            self._validate_short_product()
            prompt_only(itext('selection.pick.prompt.check.digit'), True)
            self._skip_prompt = True #don't repeat main prompt
                
        elif result == 'partial':
            logging.debug('partial product')
            self.next_state = SLOT_VERIFICATION
            self._validate_partial(self._expected_quantity)
            prompt_only(itext('selection.pick.prompt.check.digit'), True)
            self._skip_prompt = True #don't repeat main prompt

        elif result == 'skip slot':
            logging.debug('--skip slot single 1')
            self.next_state = SLOT_VERIFICATION
            self._skip_slot()
        else:
            self._verify_product_slot(result, is_scanned)
            
    
    #---------------------------------------------------------     
    def enter_qty(self):
        logging.debug('--Single task enter qty ')
        '''override to enter quantity to just prompt for quantity'''

        #Quantity verification on, or shorting, or partial, or qty verification failed        
        if (self._region["qtyVerification"] == "1"
              or self.previous_state in [QUANTITY_VERIFICATION, ENTER_QTY] #Qty verification must of failed, so reprompt quantity
              or self._short_product 
              or self._partial):
            
            additional_vocabulary={'skip slot' : False, 'partial' : False}
            
            if self._short_product:
                logging.debug('--short?')
                prompt = itext('selection.pick.prompt.short.product.quantity')
            elif self._partial:
                prompt = itext('selection.pick.prompt.partial.quantity')
            else:
                prompt = itext("selection.pick.prompt.single.prompt.quantity")

            result = prompt_digits(prompt,
                                   itext("selection.pick.prompt.pick.quantity.help"),
                                   1, len(str(self._expected_quantity)), 
                                   False, False,
                                   additional_vocabulary, hints=[str(self._expected_quantity)])
        
            if result == 'skip slot':
                logging.debug('--Skip slot in quantity')
                self.next_state = ENTER_QTY
                self._skip_slot()
            elif result == 'partial':
                logging.debug('--Partial in quantity')
                self.next_state = ENTER_QTY
                self._validate_partial(self._expected_quantity, False)
            else:
                self._picked_quantity = int(result)
                if self._picked_quantity == self._expected_quantity:
                    self._partial = False
                    
        #No prompting assume expected quantity.
        else:
            self._picked_quantity = self._expected_quantity
            self.next_state=LOT_TRACKING  

#------------------------------------------------------------
    def _skip_slot(self):
        #check if region allows
        logging.debug('--Skip Slot Method ')
        if not self._region['skipSlotAllowed']:
            prompt_only(itext('generic.skip.slot.notallowed'))
            return

        location_id = self._picks[0]['locationID']
        allowed = False
        pass_status = 'N'
        skip_status = 'S'
        #if not pick by pick, then check if another slot and pass
        if not self._region['pickByPick']:
            logging.debug('--Skip Slot pickbyPick')
            for pick in self.callingTask._picks_lut:
                if (pick['status'] not in ['P', 'X'] 
                    and pick['locationID'] != location_id): 
                    allowed = True
    
                if pick['status'] == 'B': #must be in base item pass
                    pass_status = 'B'
                    skip_status = 'N'
            
            #Last slot, not allowed to skip
            if not allowed:
                prompt_only(itext('generic.skip.slot.last'))
                return

        #confirm skip slot
        if prompt_yes_no(itext('generic.skip.slot.confirm')):
            logging.debug('--Confirm in skip method')
            for pick in self.callingTask._picks_lut:
                if pick['status'] == pass_status:
                    if pick['locationID'] == location_id:
                        pick['status'] = skip_status
            
            
            #send update status
            update_status = VoiceLinkLutOdr('prTaskLUTUpdateStatus', 
                                            'prTaskODRUpdateStatus', 
                                            self._region['useLuts'])
            
            while update_status.do_transmit(self._assignment_lut[0]['groupID'],
                                            self._picks[0]['locationID'],
                                            '0', skip_status) != 0:
                pass
            
            #End the pick prompt
            self.next_state = '' 
    
    #------------------------------------------------------------



obj_factory.set_override(PickPromptSingleTask, PickPromptSingleTask_Custom)