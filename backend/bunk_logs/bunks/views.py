import logging

from django.shortcuts import redirect
from django.shortcuts import render

from .forms import UnitForm

# Set up logger
logger = logging.getLogger(__name__)


def create_unit(request):
    if request.method == "POST":
        form = UnitForm(request.POST)
        logger.info("Processing Unit form submission")
        if form.is_valid():
            form.save()
            logger.info("New Unit created successfully")
            # Redirect or show success message
            return redirect("unit_list")  # Adjust to your URL name
        logger.warning("Form validation errors: %s", form.errors)
    else:
        form = UnitForm()
        logger.info("Displaying empty Unit form")

    return render(request, "bunks/unit_form.html", {"form": form})
