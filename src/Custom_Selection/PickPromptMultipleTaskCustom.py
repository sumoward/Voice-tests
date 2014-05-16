from vocollect_core.dialog.functions import prompt_ready , prompt_only,\
    prompt_yes_no
from vocollect_core.dialog.functions import prompt_digits, prompt_digits_required 

from vocollect_core import itext, class_factory
from selection.PickPrompt import PickPromptTask, SLOT_VERIFICATION, ENTER_QTY
from selection.PickPromptMultiple import PickPromptMultipleTask
from vocollect_core.utilities import obj_factory
from selection.SharedConstants import LOT_TRACKING
from common.VoiceLinkLut import VoiceLinkLutOdr

import logging #@UnresolvedImport
#logging.basicConfig(level=logging.DEBUG)


class PickPromptMultipleTask_Custom(PickPromptMultipleTask):
    pass
    logging.debug('**Pick prompt multiple custom')
    '''Pick prompts for regions with multiple pick prompt defined
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
        '''Multiple Prompts''' 
        logging.debug('--Pick prompt slot verification')
        result, is_scanned = prompt_digits_required(self._picks[0]["slot"],
                                                    itext("selection.pick.prompt.checkdigit.help"), 
                                                    [self._picks[0]["checkDigits"], self._pvid], 
                                                    [self._picks[0]["scannedProdID"]], 
                                                    {'ready' : False, 'skip slot' : False})
        if result == 'skip slot':
            logging.debug('--skip1')
            self.next_state = SLOT_VERIFICATION
            self._skip_slot()
        else:
            logging.debug('move on to verify', result, is_scanned)
            self._verify_product_slot(result, is_scanned)
     
    #------------------------------------------------------------
    def _verify_product_slot(self, result, is_scanned):
        '''Verifies product/slot depending on spoken check digit or spoken/scanned pvid or ready spoken'''
        #if ready is spoken and check digits is not blank prompt for check digit
        logging.debug('---verify_product_slot','result = ',result,',check digits = ',self._picks[0]["checkDigits"])
        
        if result == 'ready' and self._picks[0]["checkDigits"] != '':
            logging.debug(' we want this one')
            prompt_only(itext('selection.pick.prompt.speak.check.digit'), True)
            self.next_state = SLOT_VERIFICATION
        #if pvid is scanned verify it matches the scanned product id
        elif is_scanned:
            if self._picks[0]["scannedProdID"] != result:
                prompt_only(itext('generic.wrongValue.prompt', result))
                self.next_state = SLOT_VERIFICATION
        #if check digit is spoken and both pvid and check digits are same prompt for identical short product
        elif result == self._picks[0]["checkDigits"] and self._pvid == result:
            logging.debug('short1')
            if prompt_yes_no(itext('selection.pick.prompt.identical.product.short.product')):
                
                self._set_short_product(0)
                self.next_state = LOT_TRACKING
        #if ready or check digits  is spoken  and pvid is not blank prompt for short product
        elif result in [self._picks[0]["checkDigits"], 'ready'] and (self._pvid != '' or self._picks[0]["scannedProdID"] != ''):
            logging.debug('short2')
            if prompt_yes_no(itext("selection.pick.prompt.short.product")):
                logging.debug('short3')
                self._set_short_product(0)
                self.next_state = LOT_TRACKING
            else:
                logging.debug('short4')
                prompt_only(itext('selection.pick.prompt.wrong.pvid'))
                self.next_state = SLOT_VERIFICATION

    #------------------------------------------------------------ 
     
     
         
    #----------------------------------------------------------
    def enter_qty(self):
        ''' Enter quantity'''
        logging.debug('Pick prompt quantity::: ', self._short_product)

        additional_vocabulary = {'skip slot' : False, 'partial' : False}
            
        #prompt user for quantity
        if self._region["qtyVerification"] == "1" or self._short_product or self._partial:
            if self._short_product:
                prompt = itext('selection.pick.prompt.short.product.quantity')
            elif self._partial:
                prompt = itext('selection.pick.prompt.partial.quantity')
                additional_vocabulary['short product'] = False #Add short product to vocab
            else:
                prompt = itext("selection.pick.prompt.pick.quantity", 
                                    self._expected_quantity, self._uom, self._id_description, self._description, self._message, )
            
            result = prompt_digits(prompt,
                                   itext("selection.pick.prompt.pick.quantity.help"),
                                   1, len(str(self._expected_quantity)), 
                                   False, False,
                                   additional_vocabulary, hints=[str(self._expected_quantity)])
        else:
            additional_vocabulary['short product'] = False #Add short product to vocab
            #If the quantity verification is not set ask for quantity and take what ever they say
            result = prompt_ready(itext("selection.pick.prompt.pick.quantity", 
                                             self._expected_quantity, self._uom,  self._id_description, self._description, self._message), 
                                  False, 
                                  additional_vocabulary)

        #check results
        if result == 'short product':
            logging.debug('in short')
            self.next_state = ENTER_QTY
            self._short_product = True
            self._partial = False
        elif result == 'partial':
            self.next_state = ENTER_QTY
            self._validate_partial(self._expected_quantity)
        elif result == 'ready':
            self._picked_quantity = self._expected_quantity
        elif result == 'skip slot':
            self.next_state = ENTER_QTY
            self._skip_slot()
        else:
            self._picked_quantity = int(result)
            if self._picked_quantity == self._expected_quantity:
                self._short_product = False
                self._partial = False
    
#------------------------------------------------------------
    def _skip_slot(self):
        logging.debug('-- in skip slot' )
        
#        from pprint import pprint
        logging.debug(list(vars(self._region)))
        logging.debug(dir(self._region))
        logging.debug(self._region.__dict__)
        
        #check if region allows
        if not self._region['skipSlotAllowed']:
            prompt_only(itext('generic.skip.slot.notallowed'))
            return

        location_id = self._picks[0]['locationID']
        allowed = False
        pass_status = 'N'
        skip_status = 'S'
        #if not pick by pick, then check if another slot and pass
        if not self._region['pickByPick']:
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
   
   
obj_factory.set_override(PickPromptMultipleTask, PickPromptMultipleTask_Custom)