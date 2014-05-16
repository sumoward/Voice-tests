import mock_catalyst
from mock_catalyst import EndOfApplication
from vocollect_lut_odr_test.mock_server import MockServer, BOTH_SERVERS
from main import main

import logging #Hello Brian


logging.basicConfig(level=logging.DEBUG)
logging.debug('**Test File')

#
#create a simulated host server
#ms = MockServer(use_std_in_out = True)
#ms.start_server(BOTH_SERVERS)
##ms.set_pass_through_host('127.0.0.1', 15004, 15005)
#ms.load_server_responses("Test/Data/test1.xml")
#ms.set_server_response('Y', 'prTaskODR')
#
##Post responses
#mock_catalyst.post_dialog_responses('ready',
 #                                '123','ready' ,'ready','9')#'4!', 'yes','1!','yes'
mock_catalyst.environment_properties['Device.Id'] = 'DeviceBrianlaptop'
mock_catalyst.environment_properties['Operator.Id'] = 'brian'

try:
    logging.debug('--running test script for Dalefarm')
    main()
except EndOfApplication as err:
    print('Application ended')
    
#    
#ms.stop_server(BOTH_SERVERS)


#Sample test case creation
#from CreateTestFile import CreateTestFile
#test = CreateTestFile('Sample', ms)
#path = '' #should end with slash if specified (i.e. test\functional_tests\Selection_tests\)
#test.write_test_to_file(path)
