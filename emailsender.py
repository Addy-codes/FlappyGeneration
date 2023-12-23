from flask import Flask, render_template, session
import boto3
from botocore.exceptions import ClientError

# AWS SES configuration
AWS_REGION = "eu-north-1"  # e.g., 'us-west-2'
SENDER_EMAIL = "ankurg@chaoswale.com"  # This should be a verified email in AWS SES

def send_email(recipient, game_url):
    # The subject line for the email.
    subject = "Game URL"

    # The email body for recipients with non-HTML email clients.
    body_text = f"Here is your game URL: {game_url}"

    # The HTML body of the email.
    body_html = f"""<html>
    <head></head>
    <body>
      <h1>Game URL testing from code</h1>
      <p>Here is your game URL: <a href="{game_url}">{game_url}</a></p>
    </body>
    </html>"""

    # The character encoding for the email.
    charset = "UTF-8"

    # Create a new SES resource and specify a region.
    client = boto3.client(
        'ses',
        region_name="eu-north-1",
        aws_access_key_id="AKIARIJ3VRAIE6TY4LAI",
        aws_secret_access_key="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"
    )

    # Try to send the email.
    try:
        # Provide the contents of the email.
        response = client.send_email(
            Destination={
                'ToAddresses': [recipient],
            },
            Message={
                'Body': {
                    'Html': {
                        'Charset': charset,
                        'Data': body_html,
                    },
                    'Text': {
                        'Charset': charset,
                        'Data': body_text,
                    },
                },
                'Subject': {
                    'Charset': charset,
                    'Data': subject,
                },
            },
            Source=SENDER_EMAIL,
        )
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        print("Email sent! Message ID:"),
        print(response['MessageId'])

send_email("ankurg@chaoswale.com", "www.google.com")
