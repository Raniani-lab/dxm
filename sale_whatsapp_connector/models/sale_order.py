# See LICENSE file for full copyright and licensing details.
from odoo import models
import requests
import json
from datetime import datetime
import html2text


class SaleOrder(models.Model):
    """Inherit Sale Order."""

    _inherit = 'sale.order'

    def get_link(self):
        """Method to genrate the share Link."""
        for rec in self:
            base_url = rec.get_base_url()
            share_url = rec._get_share_url(redirect=True,
                                           signup_partner=True)
            url = base_url + share_url
            return url

    def send_order_status(self):
        """Send Message to Customer."""
        for rec in self:
            templated_id = self.env.ref('sale_whatsapp_connector.'
                                        'sale_order_status',
                                        raise_if_not_found=False)
            whatsapp_log_obj = self.env['whatsapp.message.log']
            company_id = self.env.user and\
                self.env.user.company_id or False
            company_id.check_auth()
            path = company_id and company_id.authenticate and\
                company_id.api_url + \
                str(company_id.instance_no)

            if path and rec.partner_id.country_id and\
                    rec.partner_id.mobile and templated_id:
                mobile = rec.partner_id._formatting_mobile_number()
                url_path = path + '/sendMessage'
                token_value = {'token': company_id.api_token}
                template = templated_id.generate_email(rec.id)
                body = template.get('body')
                message_data = {'phone': mobile,
                                'body': html2text.html2text(body) +
                                rec.get_link(),
                                }
                data = json.dumps(message_data)
                request_meeting = requests.post(
                    url_path, data=data, params=token_value,
                    headers={'Content-Type': 'application/json'})
                if request_meeting.status_code == 200:
                    data = json.loads(request_meeting.text)
                    chat_id = data.get('id') and\
                        data.get('id').split('_')
                    whatsapp_log_obj.create(
                        {'name': rec.partner_id.name,
                         'msg_date': datetime.now(),
                         'link': url_path,
                         'data': data,
                         'chat_id': chat_id[1],
                         'message': request_meeting.text,
                         'message_body': message_data.get('body'),
                         'status': 'send'})
                    rec.partner_id.chat_id = chat_id[1]
                else:
                    whatsapp_log_obj.create(
                        {'name': rec.partner_id.name,
                         'msg_date': datetime.now(),
                         'link': url_path,
                         'data': data,
                         'message': request_meeting.text,
                         'message_body': message_data.get('body'),
                         'status': 'error'})
