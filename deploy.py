# from os.path import join, dirname
# from dotenv import load_dotenv
# import boto3


# dotenv_path = join(dirname('.'), '.env')
# load_dotenv(dotenv_path)
#
#
# def put_rule(client):
#     response = client.put_rule(
#         Name='my-scheduled-rule',
#         ScheduleExpression='rate(1 minute)',
#         State='ENABLED',
#         Description='Invoke lambda function every minute',
#     )
#     print response.keys()
#
# def put_permission():
#     response = client.put_permission(
#     Action='lambda:InvokeFunction',
#     Principal='events.amazonaws.com',
#     StatementId='my-scheduled-event'
# )
#
# if __name__ == "__main__":
#     client = boto3.client('events')
#     put_rule(client)


import boto3
from botocore.exceptions import ClientError as BotoClientError


lambda_client = boto3.client('lambda')
events_client = boto3.client('events')


def get_lambda_function_arn(fn_name):
    response = lambda_client.get_function_configuration(
        FunctionName=fn_name,
    )
    return response['FunctionArn']


def is_function_exists(fn_name):
    try:
        get_lambda_function_arn(fn_name)
        return True
    except BotoClientError as bce:
        if bce.response['Error']['Code'] == 'ResourceNotFoundException':
            return False
        else:
            raise


def create_lambda_function(fn_role, fn_name):
    response = lambda_client.create_function(
        FunctionName=fn_name,
        Runtime='python2.7',
        Role=fn_role,
        Handler="{0}.lambda_handler".format(fn_name),
        Code={'ZipFile': open("{0}.zip".format(fn_name), 'rb').read(), },
    )
    print response


def add_permissions(fn_name, rule_name):
    try:
        response = lambda_client.add_permission(
            FunctionName=fn_name,
            StatementId="{0}-Event".format(rule_name),
            Action='lambda:InvokeFunction',
            Principal='events.amazonaws.com',
            SourceArn=get_lambda_function_arn(fn_name),
        )
        print response
    except BotoClientError as bce:
        if bce.response['Error']['Code'] == 'ResourceConflictException':
            pass
        else:
            raise


def create_lambda_function_if_needed(fn_role, fn_name):
    if not is_function_exists(fn_name):
        create_lambda_function(fn_role, fn_name)


def create_or_udpate_rule(fn_role, rule_name, frequency):
    response = events_client.put_rule(
        Name=rule_name,
        ScheduleExpression=frequency,
        State='ENABLED',
        Description='Trigger Hello World Every minute',
    )
    print response


def connect_lambda_function_to_rule(fn_arn, rule_name):
    response = events_client.put_targets(
        Rule=rule_name,
        Targets=[
            {
                'Id': "1",
                'Arn': fn_arn,
            },
        ]
    )
    print response


if __name__ == "__main__":

    aws_account_id = '156083142943'
    fn_name = "HelloWorld"
    fn_role = 'arn:aws:iam::' + aws_account_id +\
        ':role/lambda_basic_execution'
    rule_name = "{0}-Trigger".format(fn_name)
    create_lambda_function_if_needed(fn_role, fn_name)
    fn_arn = get_lambda_function_arn(fn_name)
    frequency = "rate(1 minute)"
    create_or_udpate_rule(fn_role, rule_name, frequency)
    add_permissions(fn_name, rule_name)
    connect_lambda_function_to_rule(fn_arn, rule_name)
