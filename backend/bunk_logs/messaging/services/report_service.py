from django.utils import timezone
from datetime import date, timedelta
from typing import Dict, Any

from bunk_logs.orders.models import Order, OrderType


class DailyReportService:
    """Service for generating daily order reports"""
    
    def get_orders_by_date_and_type(self, target_date: date, order_type_name: str):
        """Get all orders for a specific date and order type"""
        return Order.objects.filter(
            order_date__date=target_date,
            order_type__type_name=order_type_name
        ).select_related(
            'user', 
            'order_bunk', 
            'order_type'
        ).prefetch_related(
            'order_items__item',
            'order_items__item__item_category'
        ).order_by('order_date')
    
    def get_orders_by_date(self, target_date: date):
        """Get all orders for a specific date"""
        return Order.objects.filter(
            order_date__date=target_date
        ).select_related(
            'user', 
            'order_bunk', 
            'order_type'
        ).prefetch_related(
            'order_items__item',
            'order_items__item__item_category'
        ).order_by('order_type__type_name', 'order_date')
    
    def generate_daily_report_data(self, target_date: date = None) -> Dict[str, Any]:
        """Generate structured data for daily email report"""
        if not target_date:
            target_date = timezone.now().date()
        
        # Get orders by type
        maintenance_orders = self.get_orders_by_date_and_type(target_date, "Maintenance Request")
        camper_care_orders = self.get_orders_by_date_and_type(target_date, "Camper Care")
        
        # Get all orders for the date
        all_orders = self.get_orders_by_date(target_date)
        
        # Group orders by status
        orders_by_status = {}
        for order in all_orders:
            status = order.order_status
            if status not in orders_by_status:
                orders_by_status[status] = []
            orders_by_status[status].append(order)
        
        # Calculate summary statistics
        total_orders = all_orders.count()
        maintenance_count = maintenance_orders.count()
        camper_care_count = camper_care_orders.count()
        
        # Get unique bunks with orders
        bunks_with_orders = set()
        for order in all_orders:
            bunks_with_orders.add(order.order_bunk)
        
        return {
            'date': target_date,
            'maintenance_requests': maintenance_orders,
            'camper_care_requests': camper_care_orders,
            'all_orders': all_orders,
            'orders_by_status': orders_by_status,
            'total_orders': total_orders,
            'maintenance_count': maintenance_count,
            'camper_care_count': camper_care_count,
            'bunks_with_orders': list(bunks_with_orders),
            'bunks_with_orders_count': len(bunks_with_orders),
            'has_orders': total_orders > 0,
        }
    
    def generate_weekly_summary_data(self, end_date: date = None) -> Dict[str, Any]:
        """Generate weekly summary data (last 7 days)"""
        if not end_date:
            end_date = timezone.now().date()
        
        start_date = end_date - timedelta(days=6)  # Last 7 days including today
        
        orders = Order.objects.filter(
            order_date__date__range=[start_date, end_date]
        ).select_related(
            'user', 
            'order_bunk', 
            'order_type'
        ).prefetch_related(
            'order_items__item'
        )
        
        # Group by date
        daily_counts = {}
        for single_date in (start_date + timedelta(n) for n in range(7)):
            daily_counts[single_date] = {
                'total': 0,
                'maintenance': 0,
                'camper_care': 0,
                'orders': []
            }
        
        for order in orders:
            order_date = order.order_date.date()
            if order_date in daily_counts:
                daily_counts[order_date]['total'] += 1
                daily_counts[order_date]['orders'].append(order)
                
                if order.order_type.type_name == "Maintenance Request":
                    daily_counts[order_date]['maintenance'] += 1
                elif order.order_type.type_name == "Camper Care":
                    daily_counts[order_date]['camper_care'] += 1
        
        return {
            'start_date': start_date,
            'end_date': end_date,
            'daily_counts': daily_counts,
            'total_week_orders': orders.count(),
        }
