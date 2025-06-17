"""
Base model mixins for common functionality across the application.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _


class TestDataMixin(models.Model):
    """
    Mixin to add test data tracking to models.
    
    This allows easy identification and cleanup of dummy/testing data
    that is imported via CSVs or created for testing purposes.
    """
    is_test_data = models.BooleanField(
        default=False,
        help_text=_(
            "Mark this record as test/dummy data. "
            "Test data can be easily identified and deleted in bulk."
        ),
        verbose_name=_("Is Test Data")
    )
    
    class Meta:
        abstract = True

    @classmethod
    def get_test_data_queryset(cls):
        """Return a queryset of all test data for this model."""
        return cls.objects.filter(is_test_data=True)
    
    @classmethod
    def delete_all_test_data(cls):
        """Delete all test data for this model. Returns count of deleted objects."""
        test_data = cls.get_test_data_queryset()
        count = test_data.count()
        test_data.delete()
        return count
    
    @classmethod
    def get_production_data_queryset(cls):
        """Return a queryset of all production (non-test) data for this model."""
        return cls.objects.filter(is_test_data=False)


class TimestampedTestDataMixin(TestDataMixin):
    """
    Mixin that combines test data tracking with timestamp fields.
    
    This is useful for models that need both test data tracking
    and created/updated timestamps.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True
