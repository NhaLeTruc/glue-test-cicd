import boto3
import itertools
import subprocess
import time
import sys
from os import path

cfn = boto3.client('cloudformation')

commitID = sys.argv[1] # commit id.
pathArray = sys.argv[2:] # changed filepaths array.
ext = set(["-test.py","-script.py","-infra.yaml"]) # three critical files for testing/creating glue job

def checkDir(pathArray,ext):
    dir = set([i.split("/")[0] for i in pathArray if len(i) > 1])
    filepath = set([r[0] + "/" + r[0] + r[1] for r in itertools.product(dir, ext)])

    missing = set([m for m in filepath if not path.isfile(m)])
    ymlfiles = set([y for y in filepath if y.endswith(".yaml")])
    testfiles = set([y for y in filepath if y.endswith("-test.py")])

    if len(missing): return [False,missing]
    return [True,ymlfiles,testfiles]

# Check critical files availablility in dedicated folder.
checkresult = checkDir(pathArray,ext)

if not checkresult[0]:
    for misfile in checkresult[1]: print("Missing file: "+ misfile) 
    exit()

# Create test infrastructures.
failstack = {}
for e in checkresult[1]:
    try:
        stackname = e.split("/")[0] + '-test-' + str(commitID)
        templatebody = e
        subprocess.check_call("aws cloudformation create-stack --stack-name " + stackname + " --template-body file://" + e + " --capabilities CAPABILITY_NAMED_IAM", shell=True)
        time.sleep(30) # Delay for create-stack to start stack creation

    except Exception as e:
        failstack[stackname] = str(e)
        continue

    attempts = 0
    while attempts < 5:
        try:
            response = cfn.describe_stacks(StackName=stackname)
            if response['Stacks'][0]['StackStatus'] == 'CREATE_COMPLETE': 
                print(stackname + " was SUCCESSFULLY created") # SNS to owner.
                break
            if response['Stacks'][0]['StackStatus'] in ['CREATE_FAILED','ROLLBACK_COMPLETE','ROLLBACK_FAILED','ROLLBACK_IN_PROGRESS']: 
                failstack[stackname] = response['Stacks'][0]['StackStatus']
                break
            time.sleep(180)
            attempts+=1
            
        except Exception as e:
            failstack[stackname] = str(e)
            break
            
    else:
        failstack[stackname] = "Took too long to be created (>15 mins)"

for key, value in failstack.items(): print("stack " + key + " CREATION FAILED due to: " + value) # SNS to Senior Dev.
if len(failstack): exit()

# Run test files.
for n in checkresult[2]:
    try:
        stackname = e.split("/")[0] + '-test-' + str(commitID)
        subprocess.check_call("python " + n + " " + stackname, shell=True)
    except Exception as e:
        print('test file failed to run: ' + n) 
        print(e)  # Need handling for duplicated name or any exception. E.g. SNS to Senior Dev.
        continue