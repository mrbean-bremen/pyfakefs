import asyncio
import os
from contextlib import nullcontext as does_not_raise
from pathlib import Path
import botocore.session
import boto3
import botocore
import botocore.client
import botocore.loaders
import pytest
import s3transfer
from moto.core.decorator import mock_aws
from pyfakefs.fake_filesystem import FakeFilesystem


@pytest.fixture(scope="session", autouse=True)
def config(fs_session: FakeFilesystem):
    # ref: https://github.com/getmoto/moto/issues/1682
    # compatible with moto
    fs_session.add_real_paths(
        [
            str(Path(str(module.__file__)).parent)
            for module in [boto3, botocore, s3transfer]
        ],
        read_only=True,
        lazy_dir_read=False,
    )
    fs_session.create_file("/fw/zero-file", contents=b"")
    fs_session.create_file("/fw/random-file", contents=os.urandom(1024))

    yield fs_session
    fs_session.clear_cache()


@mock_aws
def test_aws_s3_upload():
    with does_not_raise():
        asyncio.run(__dispatch())


async def __dispatch():
    def func(file):
        with does_not_raise():
            print("check and upload file")
            assert Path(file).exists()
            client.upload_file(file, "foobar", Path(file).name)

    client = boto3.client("s3")
    client.create_bucket(Bucket="foobar")
    tasks = []
    async with asyncio.TaskGroup() as tg:
        tasks = [
            tg.create_task(asyncio.to_thread(func, file))
            for file in ["/fw/zero-file", "/fw/random-file"]
        ]
    return [task.result() for task in tasks]
