import boto3
from botocore.exceptions import ClientError as BotoClientError
import subprocess
import logging
import sys
import os
from os.path import join, dirname
from dotenv import load_dotenv

logger = logging.getLogger('thestral_deployment')
logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


def read_deploy_config():
    dotenv_path = join(dirname('.'), '.env')
    load_dotenv(dotenv_path)

    configuration = {
            'AWS_ACCESS_KEY_ID': os.getenv('AWS_ACCESS_KEY_ID'),
            'AWS_SECRET_ACCESS_KEY': os.getenv('AWS_SECRET_ACCESS_KEY'),
            'DOCKER_IMAGE': os.getenv('DOCKER_IMAGE'),
    }
    return configuration


def get_function_arn(lambda_client, fn_name):
    response = lambda_client.get_function_configuration(
        FunctionName=fn_name
    )
    return response['FunctionArn']


def get_function(lambda_client, fn_name):
    response = lambda_client.get_function(
        FunctionName=fn_name
    )
    return response


def is_function_exists(lambda_client, fn_name):
    try:
        get_function(lambda_client, fn_name)
        return True
    except BotoClientError as bce:
        if bce.response['Error']['Code'] == 'ResourceNotFoundException':
            return False
        raise


def update_function(lambda_client, fn_name):
    zip_file_name = fn_name + ".zip"
    code_file_name = fn_name + ".py"
    create_zip_file_for_code(zip_file_name, code_file_name)
    lambda_client.update_function_code(
        FunctionName=fn_name,
        Publish=True,
        ZipFile=open("{0}.zip".format(fn_name), 'rb').read()
    )


def get_rule_arn(events_client, rule_name):
    response = events_client.describe_rule(
        Name=rule_name
    )
    return response['Arn']


def create_zip_file_for_code(zip_file_name, code_file_name):
    subprocess.check_output(["zip", zip_file_name, code_file_name])


def create_function(lambda_client, fn_role, fn_name):
    zip_file_name = fn_name + ".zip"
    code_file_name = fn_name + ".py"
    create_zip_file_for_code(zip_file_name, code_file_name)
    lambda_client.create_function(
        FunctionName=fn_name,
        Runtime='python2.7',
        Role=fn_role,
        Handler="{0}.lambda_handler".format(fn_name),
        Code={'ZipFile': open("{0}.zip".format(fn_name), 'rb').read(), },
    )


def put_rule(events_client, rule_name):
    events_client.put_rule(
        Name=rule_name,
        ScheduleExpression=frequency,
        State='ENABLED',
    )


def add_permissions(lambda_client, events_client, fn_name, rule_name):
    try:
        lambda_client.add_permission(
            FunctionName=fn_name,
            StatementId="{0}-Event".format(rule_name),
            Action='lambda:InvokeFunction',
            Principal='events.amazonaws.com',
            SourceArn=get_rule_arn(events_client, rule_name),
        )
    except BotoClientError as bce:
        if not bce.response['Error']['Code'] == 'ResourceConflictException':
            raise


def put_targets(events_client, fn_arn, rule_name):
    events_client.put_targets(
        Rule=rule_name,
        Targets=[
            {
                'Id': "1",
                'Arn': fn_arn,
            },
        ]
    )


def is_compute_env_exists(batch_client, compute_env_name):
    response = batch_client.describe_compute_environments(
        computeEnvironments=[
            compute_env_name,
        ],
    )
    if len(response['computeEnvironments']) == 1:
        return True
    else:
        return False


def is_job_queue_exists(batch_client, job_queue_name):
    response = batch_client.describe_job_queues(
        jobQueues=[
            job_queue_name,
        ],
    )

    if len(response['jobQueues']) == 1:
        return True
    else:
        return False


def is_job_definition_exists(batch_client, job_definition_name):
    response = batch_client.describe_job_definitions(
        jobDefinitionName=job_definition_name,
    )
    if len(response['jobDefinitions']) >= 1:
        return True
    else:
        return False


def create_compute_env(batch_client, compute_env_name,
                       instance_types, aws_account_id):
    batch_client.create_compute_environment(
        type='MANAGED',
        computeEnvironmentName=compute_env_name,
        computeResources={
            'type': 'EC2',
            'desiredvCpus': 2,
            'instanceRole': 'ecsInstanceRole',
            'instanceTypes': instance_types,
            'maxvCpus': 256,
            'minvCpus': 2,
            'securityGroupIds': [
                'sg-6b10f90e',
            ],
            'subnets': [
                'subnet-e77c9d82',
                'subnet-350d0d41',
                'subnet-e0a380a6',
            ],
            'tags': {
                'Name': 'Batch Instance - C4OnDemand',
            },
        },
        serviceRole='arn:aws:iam::' + aws_account_id +
        ':role/service-role/AWSBatchServiceRole',
        state='ENABLED',
    )


def create_job_queue(batch_client, job_queue_name):
    batch_client.create_job_queue(
        computeEnvironmentOrder=[
            {
                'computeEnvironment': compute_env_name,
                'order': 1,
            },
        ],
        jobQueueName=job_queue_name,
        priority=1,
        state='ENABLED',
    )


def register_job_definition(batch_client, job_definition_name, docker_image):
    response = batch_client.register_job_definition(
        type='container',
        containerProperties={
            'command': [
                'python',
                'thestral_app.py',
            ],
            'image': docker_image,
            'memory': 1024*6,
            'vcpus': 2,
        },
        jobDefinitionName=job_definition_name,
    )

    logger.info(response)


def submit_job(batch_client, job_definition_name, job_name, job_queue_name):
    response = batch_client.submit_job(
        jobDefinition=job_definition_name,
        jobName=job_name,
        jobQueue=job_queue_name,
    )

    logger.info(response)


if __name__ == "__main__":
    deploy_conf = read_deploy_config()
    # lambda_client = boto3.client('lambda', region_name='us-west-2')
    # events_client = boto3.client('events', region_name='us-west-2')
    lambda_client = boto3.client('lambda')
    events_client = boto3.client('events')
    aws_account_id = '156083142943'
    fn_name = "HelloWorld"
    fn_role = 'arn:aws:iam::' + aws_account_id +\
        ':role/service-role/BatchRole'

    if is_function_exists(lambda_client, fn_name):
        update_function(lambda_client, fn_name)
    else:
        create_function(lambda_client, fn_role, fn_name)
    logger.info("Lamba function created")
    fn_arn = get_function_arn(lambda_client, fn_name)
    frequency = "rate(1 hour)"
    rule_name = "{0}-Trigger".format(fn_name)
    put_rule(events_client, rule_name)
    add_permissions(lambda_client, events_client, fn_name, rule_name)
    put_targets(events_client, fn_arn, rule_name)
    logger.info("Trigger Added")

    batch_client = boto3.client('batch')
    # batch_client = boto3.client('batch', region_name='us-west-2')
    compute_env_name = 'V4_M4OnDemand'
    job_queue_name = 'V4_M4OnDemandQueue'
    job_definition_name = 'M4OnDemandJobDefinition'
    job_name = 'M4OnDemandJob'
    # instance_types = ['m4.large']
    instance_types = ['optimal']
    docker_image = deploy_conf["DOCKER_IMAGE"]

    if not is_compute_env_exists(batch_client, compute_env_name):
        create_compute_env(
            batch_client, compute_env_name,
            instance_types,  aws_account_id
        )
    if not is_job_queue_exists(batch_client, job_queue_name):
        create_job_queue(batch_client, job_queue_name)
    register_job_definition(batch_client, job_definition_name, docker_image)
    submit_job(batch_client, job_definition_name, job_name, job_queue_name)
    logger.info("Deployed Successfully")
