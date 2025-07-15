from rest_framework import serializers
from .models import EmailTemplate, EmailRecipientGroup, EmailRecipient, EmailSchedule, EmailLog


class EmailTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailTemplate
        fields = '__all__'


class EmailRecipientSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailRecipient
        fields = '__all__'


class EmailRecipientGroupSerializer(serializers.ModelSerializer):
    recipients = EmailRecipientSerializer(many=True, read_only=True)
    recipient_count = serializers.SerializerMethodField()
    
    class Meta:
        model = EmailRecipientGroup
        fields = '__all__'
    
    def get_recipient_count(self, obj):
        return obj.recipients.filter(is_active=True).count()


class EmailScheduleSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source='template.name', read_only=True)
    group_name = serializers.CharField(source='recipient_group.name', read_only=True)
    
    class Meta:
        model = EmailSchedule
        fields = '__all__'


class EmailLogSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source='template.name', read_only=True)
    
    class Meta:
        model = EmailLog
        fields = '__all__'
