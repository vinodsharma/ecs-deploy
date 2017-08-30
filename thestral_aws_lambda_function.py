import boto3


def submit_job(batch_client, job_definition_name, job_name, job_queue_name):
    response = batch_client.submit_job(
        jobDefinition=job_definition_name,
        jobName=job_name,
        jobQueue=job_queue_name,
    )

    print(response)
    print "Checking New Version"


def lambda_handler(event, context):
    print("Starting")
    batch_client = boto3.client('batch')
    job_queue_name = 'V10_M4OnDemandQueue'
    job_definition_name = 'V10_M4OnDemandJobDefinition'
    job_name = 'V10_M4OnDemandJob'
    submit_job(batch_client, job_definition_name, job_name, job_queue_name)
    print("Ending")
