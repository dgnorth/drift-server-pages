from flask import Blueprint, request, jsonify, \
                  flash, g, redirect, url_for, \
                  render_template, make_response, current_app

from drift.utils import request_wants_json

from flask_login import login_required

from wtforms import PasswordField
from wtforms.validators import DataRequired
from adminweb.db.models import User
from adminweb.utils import sqlalchemy_tenant_session
from drift.core.resources.postgres import format_connection_string
from drift.orm import sqlalchemy_session
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from driftconfig.util import get_default_drift_config
from drift.utils import get_tier_name
from adminweb.utils.metrics import metrics_agent


from drift.orm import get_sqlalchemy_session


def conn_string(service_name):
    from drift.tenant import get_connection_string
    return get_connection_string(g.driftenv_objects, service_name=service_name)

log = logging.getLogger(__name__)
bp = Blueprint('dashboard', __name__, url_prefix='/dashboard', template_folder="dashboard")


def drift_init_extension(app, api, **kwargs):
    app.register_blueprint(bp)


def count_sql(session, sql):
    ret = session.execute(sql).first()[0]
    return int(ret)

def get_glance_stats(session, session_drift, metrics):
    num_players = 123#count_sql(session, 'SELECT COUNT(*) FROM ks_players WHERE npc = False')
    num_players_online = count_sql(session_drift, "SELECT COUNT(*) FROM ck_clients WHERE heartbeat > current_timestamp - interval '150 seconds'")
    num_logons_today = count_sql(session_drift, "SELECT COUNT(*) FROM ck_clients C INNER JOIN ck_users U ON U.user_id = C.user_id WHERE C.create_date > current_timestamp - interval '1 day'")
    num_players_today = count_sql(session_drift, "SELECT COUNT(DISTINCT C.player_id) FROM ck_clients C INNER JOIN ck_users U ON U.user_id = C.user_id WHERE C.create_date > current_timestamp - interval '1 day'")
    glance_stats = [
        {
            'title': 'Total players',
            'value': num_players,
            'icon': 'fa-user'
        },
        {
            'title': 'Players Online',
            'value': num_players_online,
            'icon': 'fa-users'
        },
        {
            'title': 'Visits last 24h',
            'value': num_logons_today,
            'icon': 'fa-sign-in'
        },
        {
            'title': 'Players last 24h',
            'value': num_players_today,
            'icon': 'fa-users'
        },
    ]

    value, diff = metrics.get_counter_glance(('active_users_last7days', '1 day'))
    glance_stats.append(
        {
            'title': '7 Day Active Users',
            'value': value,
            'diff': diff,
            'icon': 'fa-users'
        },
    )

    value, diff = metrics.get_counter_glance(('active_users_last14days', '1 day'))
    glance_stats.append(
        {
            'title': '14 Day Active Users',
            'value': value,
            'diff': diff,
            'icon': 'fa-users'
        },
    )


    value, diff = metrics.get_counter_glance(('active_users_last30days', '1 day'))
    glance_stats.append(
        {
            'title': '30 Day Active Users',
            'value': value,
            'diff': diff,
            'icon': 'fa-users'
        },
    )
    return glance_stats


@bp.route('/')
@login_required
def index():
    with metrics_agent() as metrics:
        with sqlalchemy_tenant_session(deployable_name='drift-base') as session_drift:
            glance_stats = get_glance_stats(session_drift, session_drift, metrics)

        players_created_per_day = metrics.get_counter_data(('created_users', '1 day'), 60, title='Players Created')
        player_visits_per_day = metrics.get_counter_data(('visits', '1 day'), 60, title='Visits')
        unique_visits_per_day = metrics.get_counter_data(('visits_users', '1 day'), 60, title='Unique Visits')

        series = []
        series.append({
                'name': 'visits_per_day',
                'title': 'Daily Statistics',
                'series': [players_created_per_day, player_visits_per_day, unique_visits_per_day]
                })

        pcu = metrics.get_counter_data(('logged_in_users', '10 minutes'), 2, title='PCU (testing)')

        series.append({'name': 'pcu', 'title': 'PCU', 'series': [pcu]})

    return render_template('dashboard/index.html',
                           players_created_per_day=players_created_per_day,
                           player_visits_per_day=player_visits_per_day,
                           series=series,
                           glance_stats=glance_stats
                           )
