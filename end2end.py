import smtplib
import imaplib
import argparse
import sys
import socket
import datetime
import random
import hashlib
import ssl
import time
import json

'''
    End2End mail test
    Test the sending and receiving of a mail via SMTP en IMAP
    
    Author: Maarten de Keizer
    Copyright: Markei.nl
    License: MIT https://opensource.org/licenses/MIT
'''

def get_config(argv):
    parser = argparse.ArgumentParser(description='')
    
    parser.add_argument('--email-from', required=True, help='E-mailaddress to use as from address')
    parser.add_argument('--email-to', required=True, help='E-mailaddress to use as to address')
    parser.add_argument('--prefix', default='[e2e email monitoring] ', help='Prefix the subject in the message with string')
    parser.add_argument('--check-frequency', type=int, default=2, help='Wait time between IMAP checks')
    parser.add_argument('--max-checks', type=int, default=30, help='Number of checks done before failure')
    parser.add_argument('--output-format', default='json', choices=['json','influx'], help='json [default], influx')
    
    parser.add_argument('--smtp-host', required=True, help='Address of the SMTP server')
    parser.add_argument('--smtp-port', type=int, default=587, help='Portnumber of the SMTP server, 587 [default] or 25 for example')
    parser.add_argument('--smtp-tls', default='starttls', choices=['none', 'tls', 'starttls'], help='none, tls, starttls [default]')
    parser.add_argument('--smtp-username', help='Username for SMTP transaction')
    parser.add_argument('--smtp-password', help='Password for SMTP transaction')
    
    parser.add_argument('--imap-host', required=True, help='Address of the IMAP server')
    parser.add_argument('--imap-port', type=int, default=143, help='Portnumber of the IMAP server, 143 [default] for example')
    parser.add_argument('--imap-tls', default='starttls', choices=['none', 'tls', 'starttls'], help='none, tls, starttls [default]')
    parser.add_argument('--imap-username', required=True, help='Username for IMAP transaction')
    parser.add_argument('--imap-password', required=True, help='Password for IMAP transaction')
    
    return parser.parse_args(argv)

def main(config):
    # start ssl/tls context
    context = ssl.create_default_context()
    
    # collect timestamp of start
    start_time = datetime.datetime.today()
    
    # generate subject
    hash = hashlib.md5()
    hash.update(bytearray(str(random.randint(0, 1000)) + socket.gethostname() + start_time.isoformat() + config.smtp_host + config.imap_host + config.email_from + config.email_to, 'utf-8'))
    random_string = hash.hexdigest()
    subject = config.prefix + ' ### ' + start_time.isoformat() + ' ### ' + random_string
    
    # generate headers
    headers = 'From: e2e test on ' + socket.gethostname() +  ' <' + config.email_from + '>' + '\r\n'
    headers += 'To: e2e test party for ' + socket.gethostname() + ' <' + config.email_to + '>' + '\r\n'
    headers += 'Subject: ' + subject + '\r\n'
    headers += 'User-agent: E2E e-mailtest' + '\r\n'
    headers += 'X-Hash: ' + random_string
    
    # generate body
    body = 'This e-mail is part of an end to end test for sending and receiving mail'
    
    # collect timestamp of smtp start
    start_time_smtp = datetime.datetime.today()
    
    # create SMTP connection
    smtp_conn = None
    if (config.smtp_tls == 'none' or config.smtp_tls == 'starttls'):
        smtp_conn = smtplib.SMTP(host=config.smtp_host, port=config.smtp_port)
    elif (config.smtp_tls[0] == 'tls'):
        smtp_conn = smtplib.SMTP_SSL(host=config.smtp_host, port=config.smtp_port, context=context)
    
    # send ehlo (helo for esmtp) based on hostname
    smtp_conn.ehlo(socket.gethostname())
    
    # upgrade to starttls if specified and repeat ehlo
    if (config.smtp_tls == 'starttls'):
        smtp_conn.starttls(context=context)
        smtp_conn.ehlo(socket.gethostname())
    
    # login
    if (config.smtp_username != '' and config.smtp_username != None):
        smtp_conn.login(config.smtp_username, config.smtp_password)
    
    # send mail
    smtp_conn.sendmail(config.email_from, config.email_to, headers + '\r\n\r\n' + body)
    
    # close
    smtp_conn.close()
    
    # collect timestamp of imap start
    start_time_imap = datetime.datetime.today()
    
    # create IMAP connection
    imap_conn = None
    if (config.imap_tls == 'none' or config.imap_tls == 'starttls'):
        imap_conn = imaplib.IMAP4(host=config.imap_host, port=config.imap_port)
    elif (config.imap_tls == 'tls'):
        imap_conn = imaplib.IMAP4_SSL(host=config.imap_host, port=config.imap_port, ssl_context=context)
    
    # upgrade to starttls if specified
    if (config.imap_tls == 'starttls'):
        imap_conn.starttls(ssl_context=context)
    
    # login
    imap_conn.login(config.imap_username, config.imap_password)
    
    # open inbox
    imap_conn.select('INBOX')
    
    # collect timestamp of imap search
    start_time_imap_search = datetime.datetime.today()
    
    # search for the mail
    tries = 0
    while True:
        tries = tries + 1
        typ, msgnums = imap_conn.search(None, '(SUBJECT "' + random_string +'")')
        for num in msgnums[0].split():
            typ, data = imap_conn.fetch(num, '(RFC822.HEADER)')
            for msg_part in data:
                if isinstance(msg_part[1], int) == False and msg_part[1].decode('utf-8').find(subject) > -1:
                    end_time_imap_search = datetime.datetime.today()
                    imap_conn.store(num, '+FLAGS', '\\Deleted')
                    imap_conn.close()
                    imap_conn.logout()
                    return {'success': True, 'hash': random_string, 'start': start_time, 'end': end_time_imap_search, 'start_time_smtp': start_time_smtp, 'start_time_imap': start_time_imap, 'start_time_imap_search': start_time_imap_search, 'tries': tries}
        time.sleep(config.check_frequency)
        if (tries >= config.max_checks):
            return {'success': False, 'hash': random_string, 'start': start_time, 'end': datetime.datetime.today(), 'start_time_smtp': start_time_smtp, 'start_time_imap': start_time_imap, 'start_time_imap_search': start_time_imap_search, 'tries': tries}
    
if __name__ == "__main__":
    config = get_config(sys.argv[1:])
    response = main(config)
    response['total_duration'] = (response['end'] - response['start']).microseconds
    response['smtp_duration'] = (response['start_time_imap'] - response['start_time_smtp']).microseconds
    response['imap_duration'] = (response['end'] - response['start_time_imap_search']).microseconds
    if (config.output_format == 'influx'):
        print('mail-e2e,email-from=' + config.email_from + ',email-to=' + config.email_to + ',smtp=' + config.smtp_host + ':' + str(config.smtp_port) + ',imap=' + config.imap_host + ':' + str(config.imap_port) + ' success=' + str(1 if response['success'] == True else 0) + ',total_dur=' + str(response['total_duration']) + ',smtp_dur=' + str(response['smtp_duration']) + ',imap_dur=' + str(response['imap_duration']))
    else:
        response['start'] = response['start'].isoformat()
        response['end'] = response['end'].isoformat()
        response['start_time_smtp'] = response['start_time_smtp'].isoformat()
        response['start_time_imap'] = response['start_time_imap'].isoformat()
        response['start_time_imap_search'] = response['start_time_imap_search'].isoformat()
        print(json.dumps(response))