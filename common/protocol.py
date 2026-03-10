# Message format definitions
MESSAGE_TYPES = {
    'SUBMIT_JOB': 'SUBMIT_JOB',
    'REQUEST_JOB': 'REQUEST_JOB',
    'JOB_COMPLETE': 'JOB_COMPLETE',
    'GET_RESULT': 'GET_RESULT'
}

def create_submit_job(job_type, data):
    return {
        'type': MESSAGE_TYPES['SUBMIT_JOB'],
        'job_type': job_type,
        'data': data
    }

def create_request_job(worker_id):
    return {
        'type': MESSAGE_TYPES['REQUEST_JOB'],
        'worker_id': worker_id
    }