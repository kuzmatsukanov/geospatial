import boto3
import os


class S3Operator:
    def __init__(self, aws_access_key_id, aws_secret_access_key):
        """
        Create an S3 client object
        :param aws_access_key_id: str, key id to the storage
        :param aws_secret_access_key: str, secret key to the storage
        """
        self.s3Client = boto3.client('s3',
                                     aws_access_key_id=aws_access_key_id,
                                     aws_secret_access_key=aws_secret_access_key)
        pass

    def download_zip(self, file_path, bucket_name):
        """
        Downloads zip file from s3 storage to "temp" folder. Returns zip file path
        :param file_path: str, file path in the S3 storage
        :param bucket_name: str, bucket name in the S3 storage
        :return:
        """
        # Create folder "temp"
        if not os.path.exists("temp"):
            os.makedirs("temp")

        # Get name of the zip file
        file_zip_name = file_path.split('/')[-1]

        # Download zip file to "temp" folder
        self.s3Client.download_file(Bucket=bucket_name,
                                    Key=file_path,
                                    Filename='temp/' + file_zip_name)
        return 'temp/' + file_zip_name
