import boto3


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
                'sleep',
                '10',
            ],
            'image': docker_image,
            'memory': 1024*6,
            'vcpus': 2,
        },
        jobDefinitionName=job_definition_name,
    )

    print(response)


def submit_job(batch_client, job_definition_name, job_name, job_queue_name):
    response = batch_client.submit_job(
        jobDefinition=job_definition_name,
        jobName=job_name,
        jobQueue=job_queue_name,
    )

    print(response)


if __name__ == "__main__":
    aws_account_id = '156083142943'
    batch_client = boto3.client('batch')
    compute_env_name = 'V3_M4OnDemand'
    job_queue_name = 'M4OnDemandQueue'
    job_definition_name = 'M4OnDemandJobDefinition'
    job_name = 'M4OnDemandJob'
    instance_types = ['m4.large']
    docker_repo = "vinodsharma/circleci-demo-docker"
    docker_image_tag = "459049b9305ed6d5b74f62fe5c06c7620b5e7214"
    docker_image = docker_repo + ":" + docker_image_tag

    if not is_compute_env_exists(batch_client, compute_env_name):
        create_compute_env(
            batch_client, compute_env_name,
            instance_types,  aws_account_id
        )
    if not is_job_queue_exists(batch_client, job_queue_name):
        create_job_queue(batch_client, job_queue_name)
    register_job_definition(batch_client, job_definition_name, docker_image)
    submit_job(batch_client, job_definition_name, job_name, job_queue_name)
