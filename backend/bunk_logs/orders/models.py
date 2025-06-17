from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from bunk_logs.utils.models import TestDataMixin, TimestampedTestDataMixin

class BunkLogsOrderTypeItemCategory(TestDataMixin):
    """
    Explicit through model for the many-to-many relationship between OrderType and ItemCategory.
    Using a unique name to avoid conflicts with any potential 'orders' app outside of bunk_logs.
    """
    order_type = models.ForeignKey('orders.OrderType', on_delete=models.CASCADE)
    item_category = models.ForeignKey('orders.ItemCategory', on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ('order_type', 'item_category')
        app_label = "orders"
        verbose_name = _("Order Type Item Category")
        verbose_name_plural = _("Order Type Item Categories")
        db_table = 'bunk_logs_orders_ordertype_itemcategory'

class OrderType(TestDataMixin):
    """OrderType model for categorizing orders."""
    type_name = models.CharField(max_length=100)
    type_description = models.TextField()
    item_categories = models.ManyToManyField(
        "orders.ItemCategory",
        through=BunkLogsOrderTypeItemCategory,
        through_fields=('order_type', 'item_category'),
        related_name="order_types",
        help_text="Categories of items that can be included in this order type"
    )

    class Meta:
        verbose_name = _("Order Type")
        verbose_name_plural = _("Order Types")
        app_label = "orders"
        db_table = 'bunk_logs_orders_ordertype'  # Custom table name to avoid conflicts

    def __str__(self):
        return self.type_name

class Order(TestDataMixin):
    """Order model for tracking orders made by users. For example, camper care items and maintenance requests."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders",
    )
    order_date = models.DateTimeField(auto_now_add=True)
    order_status = models.CharField(
        max_length=20,
        choices=[
            ("submitted", _("Submitted")),
            ("pending", _("Pending")),
            ("completed", _("Completed")),
            ("cancelled", _("Cancelled")),
        ],
        default="submitted"
    )
    order_bunk = models.ForeignKey(
        "bunks.Bunk",
        on_delete=models.CASCADE,
        related_name="orders",
    )
    order_type = models.ForeignKey(
        OrderType,
        on_delete=models.CASCADE,
        related_name="orders",
    )

    class Meta:
        verbose_name = _("Order")
        verbose_name_plural = _("Orders")
        ordering = ["-order_date"]
        app_label = "orders"
        db_table = 'bunk_logs_orders_order'  # Custom table name to avoid conflicts

    def __str__(self):
        return f"Order {self.id} by {self.user.username} for {self.order_bunk.name}"
        
    def get_absolute_url(self):
        return f"/orders/{self.id}/"
    def get_order_status_display(self):
        return dict(self._meta.get_field("order_status").choices).get(self.order_status, self.order_status)
    def get_order_items(self):
        return self.order_items.all()
    def get_order_date(self):
        return self.order_date.strftime("%Y-%m-%d %H:%M:%S")
    def get_order_bunk(self):
        return self.order_bunk
    
class OrderItem(TestDataMixin):
    """OrderItem model for tracking individual items within an order."""
    item = models.ForeignKey(
        "orders.Item",
        on_delete=models.CASCADE,
        related_name="order_items",
        null=True,  # Allow null temporarily to handle existing records
        blank=True,  # Corresponding form validation 
    )
    item_quantity = models.PositiveIntegerField()
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="order_items",
    )

    class Meta:
        verbose_name = _("Order Item")
        verbose_name_plural = _("Order Items")
        app_label = "orders"
        db_table = 'bunk_logs_orders_orderitem'  # Custom table name to avoid conflicts

    def __str__(self):
        return f"{self.item.item_name if self.item else 'Unknown Item'} (x{self.item_quantity})"
    
class Item(TestDataMixin):
    """Item model for tracking individual items available for order."""
    item_name = models.CharField(max_length=100)
    item_description = models.TextField()
    available = models.BooleanField(default=True)
    item_category = models.ForeignKey(
        "orders.ItemCategory",
        on_delete=models.CASCADE,
        related_name="items",
    )

    class Meta:
        verbose_name = _("Item")
        verbose_name_plural = _("Items")
        app_label = "orders"
        db_table = 'bunk_logs_orders_item'  # Custom table name to avoid conflicts

    def __str__(self):
        return self.item_name
    
class ItemCategory(TestDataMixin):
    """ItemCategory model for categorizing items available for order."""
    category_name = models.CharField(max_length=100)
    category_description = models.TextField()

    class Meta:
        verbose_name = _("Item Category")
        verbose_name_plural = _("Item Categories")
        app_label = "orders"
        db_table = 'bunk_logs_orders_itemcategory'  # Custom table name to avoid conflicts

    def __str__(self):
        return self.category_name