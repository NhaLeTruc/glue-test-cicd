import boto3
import time
import sys

cfn = boto3.client('cloudformation')

commitID = sys.argv[1] # commit id.
pathArray = sys.argv[2:] # changed filepaths array.

dir = set([i.split("/")[0] for i in pathArray if len(i) > 1])

for n in dir:
    try:
        stackname = n + '-test-' + str(commitID)
        response = cfn.delete_stack(StackName=stackname)

    except Exception as e:
        print('stack deletion FAILED due to exception. stackname: ' + stackname) 
        print(e)  # SNS to Senior Dev.

time.sleep(60)      
  
for m in dir:
    stackname = m + '-test-' + str(commitID)
    attempts = 0
    while attempts < 5:
        try:
            response = cfn.describe_stacks(StackName=stackname)
            if response['Stacks'][0]['StackStatus'] == 'DELETE_COMPLETE': 
                print(stackname + " was DELETED") # SNS to owner.
                break
            if response['Stacks'][0]['StackStatus'] == 'DELETE_FAILED': 
                print(stackname + " FAILED deletion") # SNS to Senior Dev.
                break
            time.sleep(180)
            attempts+=1
            
        except Exception as e: # Need handling STACK NOT FOUND exception
            print('Stack ' + stackname + ' FAILED to be deleted because:')
            print(e) # SNS to Senior Dev.
            break
            
    else:
        print("5 attempts reached, stack " + stackname + " took too long to be deleted (>15 mins).") # SNS to Senior Dev.