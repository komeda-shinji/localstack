import os
import json
from io import BytesIO
from localstack.utils import testutil
from localstack.utils.common import *
from localstack.utils.aws import aws_stack
from localstack.services.awslambda import lambda_api
from localstack.services.awslambda.lambda_api import (LAMBDA_RUNTIME_NODEJS,
    LAMBDA_RUNTIME_PYTHON27, LAMBDA_RUNTIME_JAVA8, use_docker)

THIS_FOLDER = os.path.dirname(os.path.realpath(__file__))
TEST_LAMBDA_PYTHON = os.path.join(THIS_FOLDER, 'lambdas', 'lambda_integration.py')
TEST_LAMBDA_NODEJS = os.path.join(THIS_FOLDER, 'lambdas', 'lambda_integration.js')
TEST_LAMBDA_JAVA = os.path.join(LOCALSTACK_ROOT_FOLDER, 'localstack', 'ext', 'java', 'target',
    'localstack-utils-tests.jar')

TEST_LAMBDA_NAME_PY = 'test_lambda_py'
TEST_LAMBDA_NAME_JS = 'test_lambda_js'
TEST_LAMBDA_NAME_JAVA = 'test_lambda_java'

TEST_LAMBDA_JAR_URL = ('https://repo.maven.apache.org/maven2/cloud/localstack/' +
    'localstack-utils/0.1.1/localstack-utils-0.1.1-tests.jar')

TEST_LAMBDA_LIBS = ['localstack', 'requests', 'psutil', 'urllib3', 'chardet', 'certifi', 'idna']


def test_upload_lambda_from_s3():

    s3_client = aws_stack.connect_to_service('s3')
    lambda_client = aws_stack.connect_to_service('lambda')

    lambda_name = 'test_lambda_%s' % short_uid()
    bucket_name = 'test_bucket_lambda'
    bucket_key = 'test_lambda.zip'

    # upload zip file to S3
    zip_file = testutil.create_lambda_archive(load_file(TEST_LAMBDA_PYTHON), get_content=True,
        libs=TEST_LAMBDA_LIBS, runtime=LAMBDA_RUNTIME_PYTHON27)
    s3_client.create_bucket(Bucket=bucket_name)
    s3_client.upload_fileobj(BytesIO(zip_file), bucket_name, bucket_key)

    # create lambda function
    lambda_client.create_function(
        FunctionName=lambda_name, Handler='handler.handler',
        Runtime=lambda_api.LAMBDA_RUNTIME_PYTHON27, Role='r1',
        Code={
            'S3Bucket': bucket_name,
            'S3Key': bucket_key
        }
    )

    # invoke lambda function
    data_before = b'{"foo": "bar"}'
    result = lambda_client.invoke(FunctionName=lambda_name, Payload=data_before)
    data_after = result['Payload'].read()
    assert json.loads(to_str(data_before)) == json.loads(to_str(data_after))


def test_lambda_runtimes():

    lambda_client = aws_stack.connect_to_service('lambda')

    # deploy and invoke lambda - Python
    zip_file = testutil.create_lambda_archive(load_file(TEST_LAMBDA_PYTHON), get_content=True,
        libs=TEST_LAMBDA_LIBS, runtime=LAMBDA_RUNTIME_PYTHON27)
    response = testutil.create_lambda_function(func_name=TEST_LAMBDA_NAME_PY,
        zip_file=zip_file, runtime=LAMBDA_RUNTIME_PYTHON27)
    result = lambda_client.invoke(FunctionName=TEST_LAMBDA_NAME_PY, Payload=b'{}')
    assert result['StatusCode'] == 200
    result_data = result['Payload'].read()
    assert to_str(result_data).strip() == '{}'

    # deploy and invoke lambda - Java
    if not os.path.exists(TEST_LAMBDA_JAVA):
        mkdir(os.path.dirname(TEST_LAMBDA_JAVA))
        download(TEST_LAMBDA_JAR_URL, TEST_LAMBDA_JAVA)
    zip_file = testutil.create_zip_file(TEST_LAMBDA_JAVA, get_content=True)
    response = testutil.create_lambda_function(func_name=TEST_LAMBDA_NAME_JAVA, zip_file=zip_file,
        runtime=LAMBDA_RUNTIME_JAVA8, handler='cloud.localstack.sample.LambdaHandler')
    result = lambda_client.invoke(FunctionName=TEST_LAMBDA_NAME_JAVA, Payload=b'{}')
    assert result['StatusCode'] == 200
    result_data = result['Payload'].read()
    assert to_str(result_data).strip() == '{}'

    if use_docker():
        # deploy and invoke lambda - Node.js
        zip_file = testutil.create_zip_file(TEST_LAMBDA_NODEJS, get_content=True)
        testutil.create_lambda_function(func_name=TEST_LAMBDA_NAME_JS,
            zip_file=zip_file, handler='lambda_integration.handler', runtime=LAMBDA_RUNTIME_NODEJS)
        result = lambda_client.invoke(FunctionName=TEST_LAMBDA_NAME_JS, Payload=b'{}')
        assert result['StatusCode'] == 200
        result_data = result['Payload'].read()
        assert to_str(result_data).strip() == '{}'
