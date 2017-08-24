import boto3
from botocore.exceptions import ClientError as BotoClientError
 
lambda_client = boto3.client('lambda')
events_client = boto3.client('events')


def get_function_arn(fn_name):
    response = lambda_client.get_function_configuration(
        FunctionName=fn_name
    )
    return response['FunctionArn']


def get_rule_arn(rule_name):
    response = events_client.describe_rule(
        Name=rule_name
    )
    return response['Arn']


def create_function(fn_role, fn_name):
    try:
        lambda_client.create_function(
            FunctionName=fn_name,
            Runtime='python2.7',
            Role=fn_role,
            Handler="{0}.lambda_handler".format(fn_name),
            Code={'ZipFile': open("{0}.zip".format(fn_name), 'rb').read(), },
        )
    except BotoClientError as bce:
        if not bce.response['Error']['Code'] == 'ResourceConflictException':
            raise


def put_rule(rule_name):
    events_client.put_rule(
        Name=rule_name,
        ScheduleExpression=frequency,
        State='ENABLED',
    )


def add_permissions(fn_name, rule_name):
    try:
        lambda_client.add_permission(
            FunctionName=fn_name,
            StatementId="{0}-Event".format(rule_name),
            Action='lambda:InvokeFunction',
            Principal='events.amazonaws.com',
            SourceArn=get_rule_arn(rule_name),
        )
    except BotoClientError as bce:
        if not bce.response['Error']['Code'] == 'ResourceConflictException':
            raise


def put_targets(fn_arn, rule_name):
    events_client.put_targets(
        Rule=rule_name,
        Targets=[
            {
                'Id': "1",
                'Arn': fn_arn,
            },
        ]
    )


if __name__ == "__main__":
    aws_account_id = '156083142943'
    fn_name = "HelloWorld"
    fn_role = 'arn:aws:iam::' + aws_account_id +\
        ':role/lambda_basic_execution'

    create_function(fn_role, fn_name)
    fn_arn = get_function_arn(fn_name)
    frequency = "rate(1 minute)"
    rule_name = "{0}-Trigger".format(fn_name)
    put_rule(rule_name)
    add_permissions(fn_name, rule_name)
    put_targets(fn_arn, rule_name)
