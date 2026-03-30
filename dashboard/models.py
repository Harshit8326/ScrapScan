from django.db import models
from django.contrib.auth.models import User

class DigitalPassport(models.Model):
    # Status options for the workflow
    STATUS_CHOICES = [
        ('pending', 'Pending Verification'),
        ('verified', 'Verified'),
    ]
    batch_group_id = models.CharField(max_length=100, blank=True, null=True)
    item_id = models.CharField(max_length=50, unique=True) # e.g., TX-2025-8821
    operator = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Material Analysis
    primary_material = models.CharField(max_length=100) # e.g., Cotton
    secondary_material = models.CharField(max_length=100, blank=True, null=True)
    material_ratio = models.CharField(max_length=20) # e.g., 60/40
    
    # Contaminants (Simplified for now)
    button_count = models.IntegerField(default=0)
    zipper_count = models.IntegerField(default=0)
    
    # Marketplace & Logic
    purity_score = models.FloatField() # Calculated based on material ratio
    weight = models.FloatField(help_text="Weight in kg")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    optimal_path = models.CharField(max_length=100, default="Chemical Recycling")

    def __str__(self):
        return f"{self.item_id} - {self.primary_material}"