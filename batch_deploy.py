import boto3
from botocore.exceptions import ClientError as BotoClientError


aws_account_id = '156083142943'
client = boto3.client('batch')
compute_env_name = 'V3_M4OnDemand'
job_queue_name = 'M4OnDemandQueue'
job_definition_name = 'M4OnDemandJobDefinition'
job_name = 'M4OnDemandJob'

instance_types = ['m4.large', 'm4.xlarge', 'm4.2xlarge']


def create_computing_environment():
    try:
        response = client.create_compute_environment(
            type='MANAGED',
            computeEnvironmentName=compute_env_name,
            computeResources={
                'type': 'EC2',
                'desiredvCpus': 2,
                'instanceRole': 'ecsInstanceRole',
                'instanceTypes': instance_types,
                'maxvCpus': 8,
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

        print(response)
    except BotoClientError as bce:
        if not bce.response['Error']['Code'] == 'ClientException':
            raise


def create_job_queue():
    try:
        response = client.create_job_queue(
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
        print(response)
    except BotoClientError as bce:
            if not bce.response['Error']['Code'] == 'ClientException':
                raise


def register_job_definition():
    response = client.register_job_definition(
        type='container',
        containerProperties={
            'command': [
                'sleep',
                '10',
            ],
            'image': 'busybox',
            'memory': 128,
            'vcpus': 1,
        },
        jobDefinitionName=job_definition_name,
    )

    print(response)


def submit_job():
    response = client.submit_job(
        jobDefinition=job_definition_name,
        jobName=job_name,
        jobQueue=job_queue_name,
    )

    print(response)


create_computing_environment()
create_job_queue()
register_job_definition()
submit_job()
