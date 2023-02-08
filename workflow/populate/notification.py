import datajoint as dj
from datajoint_utilities.dj_notification.loghandler import PopulateHandler
from datajoint_utilities.dj_notification.notifier.email_notifier import \
    HubSpotTemplateEmailNotifier
from datajoint_utilities.dj_notification.notifier.slack_notifier import \
    SlackWebhookNotifier

from workflow import db_prefix
from workflow.pipeline import ephys

__all__ = ["logger"]
logger = dj.logger

org_name, workflow_name, _ = db_prefix.split("_")
org_vm = dj.create_virtual_module("org_vm", f"{org_name}_admin_workflow")

workflow_key = (org_vm.Workflow & {"wf_db_prefix": db_prefix}).fetch1("KEY")

if hasattr(org_vm, "WorkflowNotification") and (
    org_vm.WorkflowNotification & workflow_key
):
    email_notifiers, webhook_notifiers = [], []
    for notif in (
        (org_vm.WorkflowNotification & workflow_key)
        .proj("notif_type")
        .fetch(as_dict=True)
    ):
        if notif["notif_type"] == "hubspot":
            hubspot_api_key, hubspot_email_template_id = (
                org_vm.WorkflowNotification.HubSpotTemplate & workflow_key
            ).fetch1(
                "hubspot_api_key",
                "hubspot_email_template_id",
            )
            receiver_emails = (
                org_vm.WorkflowNotification.ReceiverEmail & workflow_key
            ).fetch("receiver_email", "recipient_mode")
            primary_recipient_emails = [
                e for e, m in zip(*receiver_emails) if m == "primary"
            ]
            if not primary_recipient_emails:
                continue
            hubspot_notifier = HubSpotTemplateEmailNotifier(
                hubspot_api_key=hubspot_api_key,
                email_template_id=hubspot_email_template_id,
                primary_recipient_email=primary_recipient_emails.pop(0),
                cc_list=[e for e, m in zip(*receiver_emails) if m == "cc"]
                + primary_recipient_emails,
                bcc_list=[e for e, m in zip(*receiver_emails) if m == "bcc"],
            )
            email_notifiers.append(hubspot_notifier)
        elif notif["notif_type"] == "slack_webhook":
            webhook_url = (
                org_vm.WorkflowNotification.SlackWebhook & workflow_key
            ).fetch1("slack_webhook_url")
            slack_notifier = SlackWebhookNotifier(webhook_url=webhook_url)
            webhook_notifiers.append(slack_notifier)

    if webhook_notifiers:
        verbose_handler = PopulateHandler(
            notifiers=webhook_notifiers,
            full_table_names=[
                ephys.ProbeInsertion.full_table_name,
                ephys.EphysRecording.full_table_name,
                ephys.Clustering.full_table_name,
                ephys.CuratedClustering.full_table_name,
                ephys.WaveformSet.full_table_name,
                ephys.QualityMetrics.full_table_name,
            ],
            on_start=True,
            on_success=True,
            on_error=True,
        )
        verbose_handler.setLevel("DEBUG")
        logger.setLevel("DEBUG")
        logger.addHandler(verbose_handler)

    if email_notifiers:
        quiet_handler = PopulateHandler(
            notifiers=email_notifiers,
            full_table_names=[
                ephys.ProbeInsertion.full_table_name,
                ephys.QualityMetrics.full_table_name,
            ],
            on_start=True,
            on_success=True,
        )
        quiet_handler.setLevel("DEBUG")
        logger.setLevel("DEBUG")
        logger.addHandler(quiet_handler)
