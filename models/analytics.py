from datetime import datetime, timedelta
from models.database import load_json, save_json
from config import Config

def update_analytics(action, data):
    """Update analytics data with better tracking"""
    analytics = load_json(Config.DATABASES['analytics'])
    month_key = datetime.now().strftime('%Y-%m')
    
    if action == 'new_proposal':
        # Track new proposals (NOT as wins!)
        analytics.setdefault('monthly_proposals', {})[month_key] = \
            analytics.get('monthly_proposals', {}).get(month_key, 0) + 1
        
        # Track by office
        office = data.get('office')
        if office:
            analytics.setdefault('office_performance', {}).setdefault(office, {})
            analytics['office_performance'][office].setdefault('proposals', {})[month_key] = \
                analytics['office_performance'][office].get('proposals', {}).get(month_key, 0) + 1
    
    elif action == 'proposal_won':
        # Track actual wins (when proposal is converted to project)
        analytics.setdefault('monthly_wins', {})[month_key] = \
            analytics.get('monthly_wins', {}).get(month_key, 0) + 1
        
        fee = float(data.get('fee', 0))
        analytics.setdefault('monthly_revenue', {})[month_key] = \
            analytics.get('monthly_revenue', {}).get(month_key, 0) + fee
        
        # Track by PM
        pm = data.get('project_manager')
        if pm:
            analytics.setdefault('pm_performance', {}).setdefault(pm, {})
            analytics['pm_performance'][pm]['wins'] = \
                analytics['pm_performance'][pm].get('wins', 0) + 1
            analytics['pm_performance'][pm]['revenue'] = \
                analytics['pm_performance'][pm].get('revenue', 0) + fee
            
        # Track by office
        office = data.get('office')
        if office:
            analytics.setdefault('office_performance', {}).setdefault(office, {})
            analytics['office_performance'][office]['wins'] = \
                analytics['office_performance'][office].get('wins', 0) + 1
            analytics['office_performance'][office]['revenue'] = \
                analytics['office_performance'][office].get('revenue', 0) + fee
    
    elif action == 'project_completed':
        # Track completed projects
        analytics.setdefault('monthly_completed', {})[month_key] = \
            analytics.get('monthly_completed', {}).get(month_key, 0) + 1
    
    save_json(Config.DATABASES['analytics'], analytics)

def get_analytics():
    """Get comprehensive analytics data"""
    proposals = load_json(Config.DATABASES['proposals'])
    projects = load_json(Config.DATABASES['projects'])
    analytics = load_json(Config.DATABASES['analytics'])
    
    # Calculate different categories
    active_proposals = {k: v for k, v in proposals.items() if v.get('status') == 'pending'}
    pending_legal_projects = {k: v for k, v in projects.items() if v.get('status') == 'pending_legal'}
    pending_additional_info_projects = {k: v for k, v in projects.items() if v.get('status') == 'pending_additional_info'}
    active_projects = {k: v for k, v in projects.items() if v.get('status') == 'active'}
    completed_projects = {k: v for k, v in projects.items() if v.get('status') == 'completed'}
    lost_proposals = {k: v for k, v in proposals.items() if v.get('status') == 'lost'}
    dead_jobs = {k: v for k, v in projects.items() if v.get('status') == 'dead'}
    
    # Total counts
    total_active_items = len(active_proposals) + len(pending_legal_projects) + len(pending_additional_info_projects) + len(active_projects)
    total_completed_items = len(completed_projects) + len(lost_proposals) + len(dead_jobs)
    
    # Win rate calculation - based on proposals that have been decided
    won_proposals = {k: v for k, v in proposals.items() if v.get('status') == 'converted_to_project'}
    total_decided = len(won_proposals) + len(lost_proposals)
    win_rate = (len(won_proposals) / total_decided * 100) if total_decided > 0 else 0
    
    # Revenue calculation by office
    total_revenue = 0
    revenue_by_office = {}
    
    for proposal_num, proposal in proposals.items():
        if proposal.get('status') == 'converted_to_project':
            office = proposal.get('office', 'Unknown')
            fee = float(proposal.get('fee', 0))
            total_revenue += fee
            revenue_by_office[office] = revenue_by_office.get(office, 0) + fee
    
    # Client performance analytics
    client_performance = {}
    for proposal in proposals.values():
        client = proposal.get('client', 'Unknown')
        if client not in client_performance:
            client_performance[client] = {'total': 0, 'won': 0, 'revenue': 0, 'fees': []}
        
        client_performance[client]['total'] += 1
        fee = float(proposal.get('fee', 0))
        client_performance[client]['fees'].append(fee)
        
        if proposal.get('status') == 'converted_to_project':
            client_performance[client]['won'] += 1
            client_performance[client]['revenue'] += fee
    
    # Calculate client win rates and average fees
    for client, stats in client_performance.items():
        stats['win_rate'] = (stats['won'] / stats['total'] * 100) if stats['total'] > 0 else 0
        stats['avg_fee'] = sum(stats['fees']) / len(stats['fees']) if stats['fees'] else 0
        del stats['fees']  # Remove raw fees list to keep data clean
    
    # Project type and service type performance
    project_type_performance = {}
    service_type_performance = {}
    
    for proposal in proposals.values():
        project_type = proposal.get('project_type', 'Unknown')
        service_type = proposal.get('service_type', 'Unknown')
        
        # Project type performance
        if project_type not in project_type_performance:
            project_type_performance[project_type] = {'total': 0, 'won': 0, 'revenue': 0}
        project_type_performance[project_type]['total'] += 1
        if proposal.get('status') == 'converted_to_project':
            project_type_performance[project_type]['won'] += 1
            project_type_performance[project_type]['revenue'] += float(proposal.get('fee', 0))
        
        # Service type performance
        if service_type not in service_type_performance:
            service_type_performance[service_type] = {'total': 0, 'won': 0, 'revenue': 0}
        service_type_performance[service_type]['total'] += 1
        if proposal.get('status') == 'converted_to_project':
            service_type_performance[service_type]['won'] += 1
            service_type_performance[service_type]['revenue'] += float(proposal.get('fee', 0))
    
    # Calculate win rates for project and service types
    for perf_dict in [project_type_performance, service_type_performance]:
        for key, stats in perf_dict.items():
            stats['win_rate'] = (stats['won'] / stats['total'] * 100) if stats['total'] > 0 else 0
    
    # Fee range analysis
    all_fees = [float(p.get('fee', 0)) for p in proposals.values() if p.get('fee', 0)]
    won_fees = [float(p.get('fee', 0)) for p in won_proposals.values() if p.get('fee', 0)]
    
    fee_ranges = {
        'under_10k': len([f for f in all_fees if f < 10000]),
        '10k_50k': len([f for f in all_fees if 10000 <= f < 50000]),
        '50k_100k': len([f for f in all_fees if 50000 <= f < 100000]),
        '100k_500k': len([f for f in all_fees if 100000 <= f < 500000]),
        'over_500k': len([f for f in all_fees if f >= 500000])
    }
    
    won_fee_ranges = {
        'under_10k': len([f for f in won_fees if f < 10000]),
        '10k_50k': len([f for f in won_fees if 10000 <= f < 50000]),
        '50k_100k': len([f for f in won_fees if 50000 <= f < 100000]),
        '100k_500k': len([f for f in won_fees if 100000 <= f < 500000]),
        'over_500k': len([f for f in won_fees if f >= 500000])
    }
    
    # Project manager performance
    pm_performance = {}
    for proposal in proposals.values():
        pm = proposal.get('project_manager', 'Unknown')
        if pm not in pm_performance:
            pm_performance[pm] = {'total': 0, 'won': 0, 'revenue': 0}
        pm_performance[pm]['total'] += 1
        
        # Check if won
        if proposal.get('status') == 'converted_to_project':
            pm_performance[pm]['won'] += 1
            pm_performance[pm]['revenue'] += float(proposal.get('fee', 0))
    
    # Calculate PM win rates
    for pm, stats in pm_performance.items():
        stats['win_rate'] = (stats['won'] / stats['total'] * 100) if stats['total'] > 0 else 0
    
    # Average time to win
    win_times = []
    for proposal in won_proposals.values():
        try:
            proposal_date = proposal.get('date', '')
            won_date = proposal.get('won_date', '')
            if proposal_date and won_date:
                proposal_created = datetime.strptime(proposal_date, '%Y-%m-%d')
                proposal_won = datetime.strptime(won_date, '%Y-%m-%d')
                win_times.append((proposal_won - proposal_created).days)
        except:
            pass
    
    avg_time_to_win = sum(win_times) / len(win_times) if win_times else 0
    
    # Legal queue performance
    legal_queue_analytics = {
        'total_pending': len(pending_legal_projects),
        'avg_processing_time': 0,  # Will be calculated if we have processing time data
        'bottlenecks': []
    }
    
    # Proposal lifecycle analytics
    lifecycle_analytics = {
        'avg_proposal_to_sent': 0,
        'avg_sent_to_won': 0,
        'avg_sent_to_lost': 0
    }
    
    return {
        'win_rate': round(win_rate, 1),
        'won_proposals': len(won_proposals),
        'total_proposals': total_decided,
        'active_proposals': len(active_proposals),
        'pending_legal_projects': len(pending_legal_projects),
        'pending_additional_info_projects': len(pending_additional_info_projects),
        'active_projects': len(active_projects),
        'completed_projects': len(completed_projects),
        'lost_proposals': len(lost_proposals),
        'dead_jobs': len(dead_jobs),
        'total_active_items': total_active_items,
        'total_completed_items': total_completed_items,
        'total_revenue': total_revenue,
        'revenue_by_office': revenue_by_office,
        'pm_performance': pm_performance,
        'client_performance': client_performance,
        'project_type_performance': project_type_performance,
        'service_type_performance': service_type_performance,
        'fee_ranges': fee_ranges,
        'won_fee_ranges': won_fee_ranges,
        'avg_time_to_win': round(avg_time_to_win, 1),
        'legal_queue_analytics': legal_queue_analytics,
        'lifecycle_analytics': lifecycle_analytics,
        'monthly_data': analytics
    }

def get_enhanced_analytics():
    """Get enhanced analytics with last month proposals and legal queue count"""
    proposals = load_json(Config.DATABASES['proposals'])
    projects = load_json(Config.DATABASES['projects'])
    analytics = load_json(Config.DATABASES['analytics'])
    
    # Get last month's data
    last_month = (datetime.now() - timedelta(days=30))
    last_month_key = last_month.strftime('%Y-%m')
    last_month_name = last_month.strftime('%B %Y')
    
    # Count proposals created last month
    last_month_proposals = 0
    for proposal in proposals.values():
        try:
            if proposal.get('date', '').startswith(last_month_key):
                last_month_proposals += 1
        except:
            pass
    
    # Count legal queue items
    legal_queue_count = 0
    for project in projects.values():
        if (project.get('status') == 'pending_legal' or 
            (project.get('legal_status') and project.get('legal_status') not in ['signed', 'not_signed'])):
            legal_queue_count += 1
    
    # Calculate different categories
    active_proposals = len([p for p in proposals.values() if p.get('status') == 'pending'])
    pending_info_projects = len([p for p in projects.values() if p.get('status') == 'pending_additional_info'])
    pending_legal_projects = len([p for p in projects.values() if p.get('status') == 'pending_legal'])
    
    # Total active items
    total_active_items = active_proposals + pending_info_projects + pending_legal_projects
    
    # Win rate calculation
    won_proposals = len([p for p in proposals.values() if p.get('status') == 'converted_to_project'])
    lost_proposals = len([p for p in proposals.values() if p.get('status') == 'lost'])
    total_decided = won_proposals + lost_proposals
    win_rate = (won_proposals / total_decided * 100) if total_decided > 0 else 0
    
    return {
        'last_month_proposals': last_month_proposals,
        'last_month_name': last_month_name,
        'total_active_items': total_active_items,
        'win_rate': round(win_rate, 1),
        'won_proposals': won_proposals,
        'lost_proposals': lost_proposals,
        'legal_queue_count': legal_queue_count
    }