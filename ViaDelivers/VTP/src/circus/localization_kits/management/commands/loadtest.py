# -*- coding: utf-8 -*-
"""Load testing for the DVX API.

This throws some requests at VIA_ANALYSIS_URL and returns the results with some
timing information.

Before you go crazy with the concurrent requests, beware this implementation
uses multiprocessing and involves one subprocess per concurrent request.
(Because it was in the standard library. For more sensible resource usage, use
twisted/treq.)

Depends on the SOURCE_FILES here existing in AWS_BUCKET_STORAGE_NAME. These are
currently hardcoded and might go away if anyone decides to clean up the server.
"""
import json
from multiprocessing import Pool
import os
import time
import sys

from django.conf import settings
from django.core.management import BaseCommand, CommandError
import requests

from localization_kits.engine import API_HEADERS

DEFAULT_CONCURRENT_REQUESTS = 2
DEFAULT_TOTAL_REQUESTS = 8

counter = 0

ENGLISH_LCID = 1033

SOURCE_FILES = [
    {"type": "odt",
     "uri": "media/projects/457/assets/537/The Red-Handed League.odt",
     "id": 537, "name": "The Red-Handed League.odt"},
    {"type": "rtf",
     "uri": "media/projects/457/assets/535/A Scandal in Bohemia.rtf",
     "id": 535,
     "name": "A Scandal in Bohemia.rtf"},
    {"type": "docx",
     "uri": "media/projects/457/assets/534/A Case of Identity.docx", "id": 534,
     "name": "A Case of Identity.docx"},
    {"type": "pdf",
     "uri": "media/projects/465/assets/551/Review_Team_Report_-ESRL_Physical_Sciences.pdf", "id": 551,
     "name": "Review_Team_Report_-ESRL_Physical_Sciences.pdf"},
    {"type": "docx",
     "uri": "media/projects/457/assets/530/The Boscombe Valley Mystery.docx",
     "id": 530,
     "name": "The Boscombe Valley Mystery.docx"}
]


def new_job_id():
    global counter
    counter += 1
    return '%dN%dLT' % (os.getpid(), counter)


def source_file(worker_id):
    return SOURCE_FILES[worker_id % len(SOURCE_FILES)]


def debug(msg):
    sys.stderr.write(msg + '\n')
    sys.stderr.flush()


def analyze_kit_post(worker_id):
    """
    :rtype : requests.Response
    """
    job_id = new_job_id()

    payload = {
        "customerID": u"0",
        "customerName": u"Load Tester",
        "subjectCode": u"1",  # Standard
        "jobID": job_id,
        "jobName": "Load Test-o-Matic",
        "type": "TRANS",
        "tm": 'default',
        "UseTeamServerTM": False,
        "UseMachineTranslation": False,
        "target": [{"lcid": 1049}],
        "source": [{"lcid": ENGLISH_LCID}],
        "s3Bucket": settings.AWS_STORAGE_BUCKET_NAME,
        "file": [source_file(worker_id)]
    }

    debug("> BEGIN %s" % (job_id,))
    try:
        r = requests.post(settings.VIA_ANALYSIS_URL, data=json.dumps(payload),
                          headers=API_HEADERS, timeout=180.0)
    finally:
        debug("<  DONE %s" % (job_id,))

    return payload, r


def watch_analyze(worker_id=None):
    start = time.time()
    info = {'worker': worker_id}
    try:
        request, response = analyze_kit_post(worker_id)
    except Exception as exc:
        info['error'] = str(exc)
    else:
        info['jobID'] = request['jobID']
        info['file'] = request['file'][0]['name']
        info['http_status'] = response.status_code
        if response.status_code != 200:
            info['error_content'] = response.content
        try:
            info['api_status'] = response.json()['status']
            info['api_response'] = response.json()
        except Exception:
            pass
    finally:
        stop = time.time()

    info.update({
        'start': start,
        'stop': stop,
        'elapsed': stop - start,
    })

    return info


def do_bunches(concurrent_requests, total_requests):
    pool = Pool(processes=concurrent_requests)
    result = pool.map(watch_analyze, xrange(total_requests), 1)
    outfile_name = 'loadtest-%05d-%dx%d.json' % (
        os.getpid(), concurrent_requests, total_requests)
    with open(outfile_name, 'w') as outfile:
        json.dump(result, outfile, indent=2, sort_keys=True)
    return outfile_name


class Command(BaseCommand):
    help = 'Send some requests to the DVX API.'

    args = '<concurrent_requests> <total_requests>'


    def handle(self, *args, **kwargs):
        concurrent_requests = DEFAULT_CONCURRENT_REQUESTS
        total_requests = DEFAULT_TOTAL_REQUESTS
        if len(args) > 3:
            raise CommandError(
                "%d args is too many, expected at most 2: %s" %
                (len(args), self.args))
        elif len(args) == 2:
            concurrent_requests, total_requests = map(int, args)
        elif len(args) == 1:
            concurrent_requests = map(int, args)

        self.stdout.write(
            "# Making %d concurrent connections, %d requests" %
            (concurrent_requests, total_requests))
        outfile_name = do_bunches(concurrent_requests, total_requests)
        self.stdout.write("= Results written to %s\n" % (outfile_name,))
