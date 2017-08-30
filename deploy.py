import boto3
from botocore.exceptions import ClientError as BotoClientError
import subprocess
import logging
import sys
import os
from os.path import join, dirname
from dotenv import load_dotenv
from time import sleep

logger = logging.getLogger('thestral_deployment')
logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

lambda_client = boto3.client('lambda')
events_client = boto3.client('events')
batch_client = boto3.client('batch')
ec2_client = boto3.client('ec2')


class Deploy_Exception(Exception):
    pass


def read_deploy_config():
    dotenv_path = join(dirname('.'), '.env')
    load_dotenv(dotenv_path)

    configuration = {
            'AWS_ACCOUNT_ID': os.getenv('AWS_ACCOUNT_ID'),
            'DOCKER_IMAGE': os.getenv('DOCKER_IMAGE'),
    }
    return configuration


def get_function_arn(fn_name):
    response = lambda_client.get_function_configuration(
        FunctionName=fn_name
    )
    return response['FunctionArn']


def get_function(fn_name):
    response = lambda_client.get_function(
        FunctionName=fn_name
    )
    return response


def is_function_exists(fn_name):
    try:
        get_function(fn_name)
        return True
    except BotoClientError as bce:
        if bce.response['Error']['Code'] == 'ResourceNotFoundException':
            return False
        raise


def update_function(fn_name):
    zip_file_name = fn_name + ".zip"
    code_file_name = fn_name + ".py"
    create_zip_file_for_code(zip_file_name, code_file_name)
    lambda_client.update_function_code(
        FunctionName=fn_name,
        Publish=True,
        ZipFile=open("{0}.zip".format(fn_name), 'rb').read()
    )


def get_rule_arn(rule_name):
    response = events_client.describe_rule(
        Name=rule_name
    )
    return response['Arn']


def create_zip_file_for_code(zip_file_name, code_file_name):
    subprocess.check_output(["zip", zip_file_name, code_file_name])


def create_function(fn_role, fn_name):
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


def put_rule(rule_name):
    # frequency = "rate(1 hour)"
    frequency = "cron(0 8 ? * mon *)"
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


def is_compute_env_exists(compute_env_name):
    response = batch_client.describe_compute_environments(
        computeEnvironments=[
            compute_env_name,
        ],
    )
    if len(response['computeEnvironments']) == 1:
        return True
    else:
        return False


def is_job_queue_exists(job_queue_name):
    response = batch_client.describe_job_queues(
        jobQueues=[
            job_queue_name,
        ],
    )

    if len(response['jobQueues']) == 1:
        return True
    else:
        return False


def is_job_definition_exists(job_definition_name):
    response = batch_client.describe_job_definitions(
        jobDefinitionName=job_definition_name,
    )
    if len(response['jobDefinitions']) >= 1:
        return True
    else:
        return False


def get_default_vpc_id():
    vpcs_info = ec2_client.describe_vpcs(
        Filters=[
            {
                'Name': 'isDefault',
                'Values': [
                    'true',
                ]
            },
        ],
    )
    if len(vpcs_info['Vpcs']) < 1:
        raise Deploy_Exception("No Default VPC Exists")
    vpc_id = vpcs_info['Vpcs'][0]['VpcId']
    return vpc_id


def get_security_group_ids(vpc_id):
    security_groups_info = ec2_client.describe_security_groups(
        Filters=[
            {
                'Name': 'vpc-id',
                'Values': [
                    vpc_id,
                ]
            },
        ],
    )
    if len(security_groups_info['SecurityGroups']) < 1:
        raise Deploy_Exception(
            "No SecurityGroup exits for the vpc-id %s" % vpc_id)

    security_group_ids = []
    for security_group in security_groups_info['SecurityGroups']:
        security_group_ids.append(security_group['GroupId'])
    return security_group_ids


def get_subnet_ids(vpc_id):
    subnets_info = ec2_client.describe_subnets(
        Filters=[
            {
                'Name': 'vpc-id',
                'Values': [
                    vpc_id,
                ]
            },
        ],
    )
    if len(subnets_info['Subnets']) < 1:
        raise Deploy_Exception("No Subnet exits for the vpc-id %s" % vpc_id)

    subnet_ids = []
    for subnet in subnets_info['Subnets']:
        subnet_ids.append(subnet['SubnetId'])
    return subnet_ids


def create_compute_env(compute_env_name, aws_account_id):
    vpc_id = get_default_vpc_id(ec2_client)
    instance_types = [
        'optimal', 'c3', 'c3.2xlarge', 'c3.4xlarge', 'c3.8xlarge', 'c3.large',
        'c3.xlarge', 'c4', 'c4.2xlarge', 'c4.4xlarge', 'c4.8xlarge',
        'c4.large', 'c4.xlarge', 'd2', 'd2.2xlarge', 'd2.4xlarge',
        'd2.8xlarge', 'd2.xlarge', 'g2', 'g2.2xlarge', 'g2.8xlarge', 'g3',
        'g3.16xlarge', 'g3.4xlarge', 'g3.8xlarge', 'i2', 'i2.2xlarge',
        'i2.4xlarge', 'i2.8xlarge', 'i2.xlarge', 'i3', 'i3.16xlarge',
        'i3.2xlarge', 'i3.4xlarge', 'i3.8xlarge', 'i3.xlarge', 'm3',
        'm3.2xlarge', 'm3.large', 'm3.medium', 'm3.xlarge', 'm4',
        'm4.10xlarge', 'm4.16xlarge', 'm4.2xlarge', 'm4.4xlarge', 'm4.large',
        'm4.xlarge', 'p2', 'p2.16xlarge', 'p2.8xlarge', 'p2.xlarge', 'r3',
        'r3.2xlarge', 'r3.4xlarge', 'r3.8xlarge', 'r3.large', 'r3.xlarge',
        'r4', 'r4.16xlarge', 'r4.2xlarge', 'r4.4xlarge', 'r4.8xlarge',
        'r4.large', 'r4.xlarge', 'x1', 'x1.16xlarge', 'x1.32xlarge'
    ]
    batch_client.create_compute_environment(
        type='MANAGED',
        computeEnvironmentName=compute_env_name,
        computeResources={
            'type': 'EC2',
            'instanceRole': 'arn:aws:iam::' + aws_account_id +
            ':instance-profile/ecsInstanceRole',
            'instanceTypes': instance_types,
            'maxvCpus': 256,
            'minvCpus': 0,
            'securityGroupIds': get_security_group_ids(ec2_client, vpc_id),
            'subnets': get_subnet_ids(ec2_client, vpc_id),
            'tags': {
                'Name': 'Batch Instance - '+compute_env_name,
            },
        },
        serviceRole='arn:aws:iam::' + aws_account_id +
        ':role/service-role/AWSBatchServiceRole',
        state='ENABLED',
    )


def wait_until_compute_env_is_ready(compute_env_name):
    for i in range(30):
        sleep(10)
        response = batch_client.describe_compute_environments(
            computeEnvironments=[compute_env_name])
        comp_env = response['computeEnvironments'][0]
        if comp_env['status'] == 'VALID':
            return
    raise Deploy_Exception(
        "TimeOut: Compute Environemnt %s is not ready" % compute_env_name)


def wait_until_job_queue_is_ready(job_queue_name):
    for i in range(30):
        sleep(10)
        response = batch_client.describe_job_queues(jobQueues=[job_queue_name])
        job_queue = response['jobQueues'][0]
        if job_queue['status'] == 'VALID':
            return
    raise Deploy_Exception(
        "TimeOut: Job Queue %s is not ready" % job_queue_name)


def create_job_queue(job_queue_name, compute_env_name):
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


def register_job_definition(job_definition_name, docker_image):
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
    return response


def submit_job(job_definition_name, job_name, job_queue_name):
    response = batch_client.submit_job(
        jobDefinition=job_definition_name,
        jobName=job_name,
        jobQueue=job_queue_name,
    )
    return response


def main():
    deploy_conf = read_deploy_config()
    docker_image = deploy_conf["DOCKER_IMAGE"]

    aws_account_id = boto3.client('sts').get_caller_identity().get('Account')
    fn_name = "thestral_aws_lambda_function"
    fn_role = 'arn:aws:iam::' + aws_account_id + ':role/LambdaBatch'
    if is_function_exists(fn_name):
        update_function(fn_name)
    else:
        create_function(fn_role, fn_name)
    logger.info("Lambda function %s created" % fn_name)
    fn_arn = get_function_arn(fn_name)
    rule_name = "{0}-Trigger".format(fn_name)
    put_rule(rule_name)
    add_permissions(fn_name, rule_name)
    put_targets(fn_arn, rule_name)
    logger.info("Cloudwatch trigger %s added/updated" % rule_name)

    compute_env_name = 'thestral_comp_env'
    job_queue_name = 'thestral_job_queue'
    job_definition_name = 'thestral_job_definition'

    if not is_compute_env_exists(compute_env_name):
        create_compute_env(compute_env_name, aws_account_id)
        logger.info("Compute environment %s is created" % compute_env_name)
        logger.info("Waiting for compute environment to be ready")
        wait_until_compute_env_is_ready(compute_env_name)
    if not is_job_queue_exists(job_queue_name):
        create_job_queue(job_queue_name, compute_env_name)
        logger.info("Job queue %s is created" % job_queue_name)
        logger.info("Waiting for job queue to be ready")
        wait_until_job_queue_is_ready(job_queue_name)
    register_job_definition(job_definition_name, docker_image)
    logger.info("Job definition is registered")
    logger.info("Deployed Successfully")


if __name__ == "__main__":
    main()
