import boto3
from botocore.exceptions import ClientError as BotoClientError
 
lambda_client = boto3.client('lambda')
events_client = boto3.client('events')
aws_account_id = '156083142943'
fn_name = "HelloWorld"
fn_role = 'arn:aws:iam::' + aws_account_id +\
    ':role/lambda_basic_execution'


def get_lambda_function_arn(fn_name):
    response = lambda_client.get_function_configuration(
        FunctionName=fn_name,
    )
    return response['FunctionArn']


try:
    fn_response = lambda_client.create_function(
        FunctionName=fn_name,
        Runtime='python2.7',
        Role=fn_role,
        Handler="{0}.lambda_handler".format(fn_name),
        Code={'ZipFile': open("{0}.zip".format(fn_name), 'rb').read(), },
    )
except BotoClientError as bce:
    if not bce.response['Error']['Code'] == 'ResourceConflictException':
        raise

 
fn_arn = get_lambda_function_arn(fn_name)
frequency = "rate(1 minute)"
name = "{0}-Trigger".format(fn_name)
 
rule_response = events_client.put_rule(
    Name=name,
    ScheduleExpression=frequency,
    State='ENABLED',
)

try:
    lambda_client.add_permission(
        FunctionName=fn_name,
        StatementId="{0}-Event".format(name),
        Action='lambda:InvokeFunction',
        Principal='events.amazonaws.com',
        SourceArn=rule_response['RuleArn'],
    )
except BotoClientError as bce:
    if not bce.response['Error']['Code'] == 'ResourceConflictException':
        raise

events_client.put_targets(
    Rule=name,
    Targets=[
        {
            'Id': "1",
            'Arn': fn_arn,
        },
    ]
)
