from flask import Blueprint, request, jsonify, \
                  flash, g, redirect, url_for, \
                  render_template, make_response

from flask_login import login_required
import logging

from drift.utils import request_wants_json
from drift.core.extensions.tenancy import tenant_from_hostname
from drift.utils import get_tier_name

from driftserverpages.utils import sqlalchemy_tenant_session

log = logging.getLogger(__name__)
bp = Blueprint('config', __name__, url_prefix='/config', template_folder="config")


@bp.route('/')
@login_required
def index():
    return render_template('config/index.html')
