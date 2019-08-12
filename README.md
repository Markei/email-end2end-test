# email-end2end-test

An end-to-end test for e-mail (SMTP en IMAP) in Python.

When you run your own e-mailservices (Postifx, Dovecot for example) you want 
to make sure is everything is okay. You can fallback on doing soms test 
specified on your MTA and MDA. But it also possible to run a full send and
delivery test. This script will support that scenario.

For best real life results you need an external mailservice (Google Gmail for
example) with SMTP and/or IMAP support.

When you supporting sending and receiving mail it is advisable to run 2 test
own from your own server (SMTP) to the external (IMAP). And one from the
external (SMTP) to your local (IMAP).

## Requirements

Python 3

## Output

The script supports the output in JSON and Influx line format (ready to be
used in Telegraf with the exec input plugin)

## How does it work

First it generates a random string. Then it sends a mail via the SMTP server
to the target address. Then it starts polling the IMAP server for a message 
with that string. Thats all.

## Options

At least you need to configure the following options, the most have a clear name

    --email-from alice@my-domain
    --email-to bob@other-domain
    
    --smtp-host mail.my-domain
    --smtp-username alice
    --smtp-password secret
    --imap-host mail.other-domain
    --imap-username bob
    --imap-password secret

Other options

    --prefix                    Prefix e-mail subject with the value, default '[e2e email monitoring] '
    --check-frequency           Run IMAP search each n-seconds, default 2
    --max-checks                Limit number of IMAP searchs, if not found in check-frequency * max checks, success=0
    --output-format             json is default, other influx
    --smtp-port                 Default: 587
    --smtp-tls                  Options: none, tls, starttls [default]
    --imap-port                 Default: 143
    --imap-tls                  Options: none, tls, starttls [default]

## Output JSON

    success                     Found e-mail in IMAP in time
    hash                        The used random string
    start                       Timestamp start the script
    start_time_smtp             Timestamp the SMTP part starts
    start_time_imap             Timestamp the SMTP part ends, the IMAP part starts
    start_time_imap_search      Timestamp the IMAP connection is setup, search starts
    tries                       Number of tried needed to find the e-mail
    end                         Timestamp the script is done
    total_duration              Delta between end and start
    smtp_duration               Delta between start_time_imap and start_time_smtp
    imap_duration               Delta between end and start_time_imap
    
## Output Influx (telegraf)

Measurement:

    mail-e2e

Tags:
    
    email-from                  The e-mail from address
    email-to                    The e-mail to address
    smtp                        SMTP host and port number (seperated by :)
    imap                        SMTP host and port number (seperated by :)

Field set:

    success                     Found e-mail in IMAP in time
    total_dur                   Delta between end and start
    smtp_dur                    Delta between start_time_imap and start_time_smtp
    imap_dur                    Delta between end and start_time_imap


## Examples

Running on the commandline. When on your system Python 2 is still the default,
replace python with *python3*

    python --email-from alice@my-domain --email-to bob@other-domain --smtp-host mail.my-domain --smtp-username alice --smtp-password secret --imap-host mail.otherdomain --imap-username bon --imap-password secret

Running in Telegraf

    [[inputs.exec]]
      commands = ["python /path/to/end2end.py --output-format influx --email-from alice@my-domain --email-to bob@other-domain --smtp-host mail.my-domain --smtp-username alice --smtp-password secret --imap-host mail.otherdomain --imap-username bon --imap-password secret"]
      timeout="80s"
      # to run each hour
      interval = 3600s


## Notes

### For SMTP/IMAP users with advanced auth mechanism (Google Gmail)

This script does only support plain auth. So for Gmail for example you need to 
create an app password (https://support.google.com/accounts/answer/185833) 
instead of using your own password.

### Keeping the passwords secure

Your password here is placed directly as an arguments. This makes the script 
very simple to understand but this is also a security risk. When you run the 
script in Telegraf make sure the access to your telegraf config is limited.

## Happy flow

The script does not properly handle auth. failures, connection timeouts on the
SMTP or IMAP server. The script simply dies when bad things happens.