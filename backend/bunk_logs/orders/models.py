from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

class Order(models.Model):
    """Order model for tracking orders made by users. For example, camper care items and maintenance requests."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders",
    )
    order_date = models.DateTimeField(auto_now_add=True)
    order_number = models.CharField(max_length=20, unique=True)
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

    class Meta:
        verbose_name = _("Order")
        verbose_name_plural = _("Orders")
        ordering = ["-order_date"]
        app_label = "orders"

    def __str__(self):
        return f"Order {self.order_number} by {self.user.username} for {self.order_bunk.name}"
    def get_absolute_url(self):
        return f"/orders/{self.id}/"
    def get_order_status_display(self):
        return dict(self._meta.get_field("order_status").choices).get(self.order_status, self.order_status)
    def get_order_items(self):
        return self.order_items.all()
    def get_order_date(self):
        return self.order_date.strftime("%Y-%m-%d %H:%M:%S")
    def get_order_number(self):
        return self.order_number
    def get_order_bunk(self):
        return self.order_bunk
    
class OrderItem(models.Model):
    """OrderItem model for tracking individual items within an order."""
    item_name = models.CharField(max_length=100)
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

    def __str__(self):
        return f"{self.item_name} (x{self.item_quantity})"
    
class Item(models.Model):
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

    def __str__(self):
        return self.item_name
    
class ItemCategory(models.Model):
    """ItemCategory model for categorizing items available for order."""
    category_name = models.CharField(max_length=100)
    category_description = models.TextField()

    class Meta:
        verbose_name = _("Item Category")
        verbose_name_plural = _("Item Categories")
        app_label = "orders"

    def __str__(self):
        return self.category_name