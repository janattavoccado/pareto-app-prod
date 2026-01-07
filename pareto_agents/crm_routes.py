"""
CRM API Routes

Provides Flask endpoints for:
- Admin: View all tenant CRM data
- Users: View/manage their tenant's CRM data
- Lead CRUD operations

File location: pareto_agents/crm_routes.py
"""

import logging
import json
from datetime import datetime
from flask import Blueprint, request, jsonify

from .auth import require_auth
from .user_auth import require_user_auth
from .database import get_db_session, Tenant, User
from .crm_models import CRMLead, LeadStatus, LeadPriority
from .crm_service import CRMService

logger = logging.getLogger(__name__)

# Create blueprints
crm_admin_bp = Blueprint('crm_admin', __name__, url_prefix='/api/admin/crm')
crm_user_bp = Blueprint('crm_user', __name__, url_prefix='/api/crm')


# ============================================================================
# Admin CRM Routes (Access to all tenants)
# ============================================================================

@crm_admin_bp.route('/leads', methods=['GET'])
@require_auth
def admin_get_leads():
    """Get all leads (admin can filter by tenant)"""
    try:
        tenant_id = request.args.get('tenant_id', type=int)
        status = request.args.get('status')
        priority = request.args.get('priority')
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        session = get_db_session()
        try:
            crm_service = CRMService(session)
            leads = crm_service.get_all_leads(
                status=status,
                priority=priority,
                tenant_id=tenant_id,
                limit=limit,
                offset=offset
            )
            
            # Get stats for the dashboard
            stats_data = crm_service.get_lead_stats(tenant_id=tenant_id)
            stats = {
                'total': stats_data.get('total', 0),
                'open': stats_data.get('by_status', {}).get('Open', 0),
                'in_progress': stats_data.get('by_status', {}).get('In Progress', 0),
                'high_priority': stats_data.get('by_priority', {}).get('High', 0)
            }
            
            return jsonify({
                'success': True,
                'leads': [lead.to_dict() for lead in leads],
                'count': len(leads),
                'stats': stats
            }), 200
        finally:
            session.close()
    except Exception as e:
        logger.error(f"Admin get leads error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


@crm_admin_bp.route('/leads/<int:lead_id>', methods=['GET'])
@require_auth
def admin_get_lead(lead_id):
    """Get a specific lead by ID (admin access)"""
    try:
        session = get_db_session()
        try:
            crm_service = CRMService(session)
            lead = crm_service.get_lead_by_id(lead_id)
            
            if not lead:
                return jsonify({'success': False, 'message': 'Lead not found'}), 404
            
            return jsonify({
                'success': True,
                'lead': lead.to_dict()
            }), 200
        finally:
            session.close()
    except Exception as e:
        logger.error(f"Admin get lead error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


@crm_admin_bp.route('/leads/<int:lead_id>', methods=['PUT'])
@require_auth
def admin_update_lead(lead_id):
    """Update a lead (admin access)"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        session = get_db_session()
        try:
            crm_service = CRMService(session)
            lead = crm_service.update_lead(
                lead_id=lead_id,
                lead_subject=data.get('lead_subject'),
                priority=data.get('priority'),
                owner=data.get('owner'),
                status=data.get('status')
            )
            
            if not lead:
                return jsonify({'success': False, 'message': 'Lead not found'}), 404
            
            return jsonify({
                'success': True,
                'lead': lead.to_dict()
            }), 200
        finally:
            session.close()
    except Exception as e:
        logger.error(f"Admin update lead error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


@crm_admin_bp.route('/leads/<int:lead_id>', methods=['DELETE'])
@require_auth
def admin_delete_lead(lead_id):
    """Delete a lead (admin access)"""
    try:
        session = get_db_session()
        try:
            crm_service = CRMService(session)
            deleted = crm_service.delete_lead(lead_id)
            
            if not deleted:
                return jsonify({'success': False, 'message': 'Lead not found'}), 404
            
            return jsonify({
                'success': True,
                'message': 'Lead deleted successfully'
            }), 200
        finally:
            session.close()
    except Exception as e:
        logger.error(f"Admin delete lead error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


@crm_admin_bp.route('/stats', methods=['GET'])
@require_auth
def admin_get_stats():
    """Get CRM statistics (admin can filter by tenant)"""
    try:
        tenant_id = request.args.get('tenant_id', type=int)
        
        session = get_db_session()
        try:
            crm_service = CRMService(session)
            stats = crm_service.get_lead_stats(tenant_id=tenant_id)
            
            return jsonify({
                'success': True,
                'stats': stats
            }), 200
        finally:
            session.close()
    except Exception as e:
        logger.error(f"Admin get stats error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


@crm_admin_bp.route('/tenants', methods=['GET'])
@require_auth
def admin_get_tenants_for_crm():
    """Get list of tenants for CRM dropdown"""
    try:
        session = get_db_session()
        try:
            tenants = session.query(Tenant).filter(Tenant.is_active == True).all()
            
            return jsonify({
                'success': True,
                'tenants': [
                    {
                        'id': t.id,
                        'company_name': t.company_name,
                        'company_slug': t.company_slug
                    } for t in tenants
                ]
            }), 200
        finally:
            session.close()
    except Exception as e:
        logger.error(f"Admin get tenants error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


# ============================================================================
# User CRM Routes (Tenant-isolated access)
# ============================================================================

@crm_user_bp.route('/leads', methods=['GET'])
@require_user_auth
def user_get_leads():
    """Get leads for user's tenant"""
    try:
        user_info = request.user_info
        tenant_id = user_info['tenant_id']
        user_id = user_info['user_id']
        
        status = request.args.get('status')
        priority = request.args.get('priority')
        my_leads = request.args.get('my_leads', '').lower() == 'true'
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        session = get_db_session()
        try:
            crm_service = CRMService(session)
            leads = crm_service.get_leads_by_tenant(
                tenant_id=tenant_id,
                status=status,
                priority=priority,
                limit=limit,
                offset=offset
            )
            
            # Filter by user if my_leads is true
            if my_leads:
                leads = [l for l in leads if l.user_id == user_id]
            
            # Get stats for the dashboard
            stats_data = crm_service.get_lead_stats(tenant_id=tenant_id)
            
            # Count user's own leads
            all_leads = crm_service.get_leads_by_tenant(tenant_id=tenant_id)
            my_lead_count = len([l for l in all_leads if l.user_id == user_id])
            
            stats = {
                'total': stats_data.get('total', 0),
                'open': stats_data.get('by_status', {}).get('Open', 0),
                'in_progress': stats_data.get('by_status', {}).get('In Progress', 0),
                'my_leads': my_lead_count
            }
            
            return jsonify({
                'success': True,
                'leads': [lead.to_dict() for lead in leads],
                'count': len(leads),
                'stats': stats
            }), 200
        finally:
            session.close()
    except Exception as e:
        logger.error(f"User get leads error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


@crm_user_bp.route('/leads', methods=['POST'])
@require_user_auth
def user_create_lead():
    """Create a new lead (with LLM extraction)"""
    try:
        user_info = request.user_info
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({'success': False, 'message': 'Message is required'}), 400
        
        session = get_db_session()
        try:
            crm_service = CRMService(session)
            lead = crm_service.create_lead(
                message=data['message'],
                tenant_id=user_info['tenant_id'],
                user_id=user_info['user_id']
            )
            
            return jsonify({
                'success': True,
                'lead': lead.to_dict()
            }), 201
        finally:
            session.close()
    except Exception as e:
        logger.error(f"User create lead error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


@crm_user_bp.route('/leads/<int:lead_id>', methods=['GET'])
@require_user_auth
def user_get_lead(lead_id):
    """Get a specific lead (tenant-isolated)"""
    try:
        user_info = request.user_info
        tenant_id = user_info['tenant_id']
        
        session = get_db_session()
        try:
            crm_service = CRMService(session)
            lead = crm_service.get_lead_by_id(lead_id, tenant_id=tenant_id)
            
            if not lead:
                return jsonify({'success': False, 'message': 'Lead not found'}), 404
            
            return jsonify({
                'success': True,
                'lead': lead.to_dict()
            }), 200
        finally:
            session.close()
    except Exception as e:
        logger.error(f"User get lead error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


@crm_user_bp.route('/leads/<int:lead_id>', methods=['PUT'])
@require_user_auth
def user_update_lead(lead_id):
    """Update a lead (tenant-isolated)"""
    try:
        user_info = request.user_info
        tenant_id = user_info['tenant_id']
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        session = get_db_session()
        try:
            crm_service = CRMService(session)
            lead = crm_service.update_lead(
                lead_id=lead_id,
                tenant_id=tenant_id,
                lead_subject=data.get('lead_subject'),
                priority=data.get('priority'),
                owner=data.get('owner'),
                status=data.get('status')
            )
            
            if not lead:
                return jsonify({'success': False, 'message': 'Lead not found'}), 404
            
            return jsonify({
                'success': True,
                'lead': lead.to_dict()
            }), 200
        finally:
            session.close()
    except Exception as e:
        logger.error(f"User update lead error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


@crm_user_bp.route('/leads/<int:lead_id>', methods=['DELETE'])
@require_user_auth
def user_delete_lead(lead_id):
    """Delete a lead (tenant-isolated)"""
    try:
        user_info = request.user_info
        tenant_id = user_info['tenant_id']
        
        session = get_db_session()
        try:
            crm_service = CRMService(session)
            deleted = crm_service.delete_lead(lead_id, tenant_id=tenant_id)
            
            if not deleted:
                return jsonify({'success': False, 'message': 'Lead not found'}), 404
            
            return jsonify({
                'success': True,
                'message': 'Lead deleted successfully'
            }), 200
        finally:
            session.close()
    except Exception as e:
        logger.error(f"User delete lead error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


@crm_user_bp.route('/stats', methods=['GET'])
@require_user_auth
def user_get_stats():
    """Get CRM statistics for user's tenant"""
    try:
        user_info = request.user_info
        tenant_id = user_info['tenant_id']
        
        session = get_db_session()
        try:
            crm_service = CRMService(session)
            stats = crm_service.get_lead_stats(tenant_id=tenant_id)
            
            return jsonify({
                'success': True,
                'stats': stats
            }), 200
        finally:
            session.close()
    except Exception as e:
        logger.error(f"User get stats error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An error occurred'}), 500
