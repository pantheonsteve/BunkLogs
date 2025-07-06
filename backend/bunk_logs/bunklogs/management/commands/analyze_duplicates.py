from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Count
from bunk_logs.bunklogs.models import BunkLog, CounselorLog


class Command(BaseCommand):
    help = 'Analyze potential duplicate records that could cause constraint violations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--bunklogs-only',
            action='store_true',
            help='Only analyze BunkLog records, skip CounselorLog records',
        )
        parser.add_argument(
            '--counselorlogs-only',
            action='store_true',
            help='Only analyze CounselorLog records, skip BunkLog records',
        )

    def handle(self, *args, **options):
        bunklogs_only = options['bunklogs_only']
        counselorlogs_only = options['counselorlogs_only']
        
        self.stdout.write(self.style.WARNING("🔍 Analyzing potential duplicate records..."))
        self.stdout.write("=" * 80)
        
        if bunklogs_only and counselorlogs_only:
            self.stdout.write(self.style.ERROR("Cannot use both --bunklogs-only and --counselorlogs-only"))
            return
        
        # Analyze BunkLogs
        if not counselorlogs_only:
            self.analyze_bunklog_duplicates()
        
        # Analyze CounselorLogs
        if not bunklogs_only:
            self.analyze_counselorlog_duplicates()

    def analyze_bunklog_duplicates(self):
        self.stdout.write(self.style.SUCCESS("\n📋 Analyzing BunkLog potential duplicates..."))
        
        # Find records that would create duplicates if date is adjusted
        potential_issues = []
        
        for log in BunkLog.objects.all().order_by('id'):
            created_date = timezone.localtime(log.created_at).date()
            
            # Only check records that need fixing (date mismatch)
            if log.date != created_date:
                # Check if adjusting this record would create a duplicate
                existing_with_new_date = BunkLog.objects.filter(
                    bunk_assignment=log.bunk_assignment,
                    date=created_date
                ).exclude(id=log.id)
                
                if existing_with_new_date.exists():
                    try:
                        camper_name = f"{log.bunk_assignment.camper.first_name} {log.bunk_assignment.camper.last_name}"
                    except:
                        camper_name = "Unknown"
                        
                    conflicting_log = existing_with_new_date.first()
                    try:
                        conflicting_camper = f"{conflicting_log.bunk_assignment.camper.first_name} {conflicting_log.bunk_assignment.camper.last_name}"
                    except:
                        conflicting_camper = "Unknown"
                    
                    potential_issues.append({
                        'log': log,
                        'camper_name': camper_name,
                        'current_date': log.date,
                        'target_date': created_date,
                        'conflicting_log': conflicting_log,
                        'conflicting_camper': conflicting_camper,
                        'description': log.description[:100] + '...' if len(log.description) > 100 else log.description,
                        'conflicting_description': conflicting_log.description[:100] + '...' if len(conflicting_log.description) > 100 else conflicting_log.description
                    })
        
        self.stdout.write(f"Found {len(potential_issues)} BunkLog records that would create duplicates")
        
        if potential_issues:
            self.stdout.write("\n🚨 Potential duplicate conflicts:")
            self.stdout.write("=" * 100)
            
            for issue in potential_issues:
                self.stdout.write(f"\nID {issue['log'].id}: {issue['camper_name']}")
                self.stdout.write(f"  Current date: {issue['current_date']} → Target date: {issue['target_date']}")
                self.stdout.write(f"  Description: {issue['description'] or 'No description'}")
                self.stdout.write(f"  CONFLICTS WITH:")
                self.stdout.write(f"    ID {issue['conflicting_log'].id}: {issue['conflicting_camper']}")
                self.stdout.write(f"    Date: {issue['conflicting_log'].date}")
                self.stdout.write(f"    Description: {issue['conflicting_description'] or 'No description'}")
                
                # Check if these might be actual duplicates or legitimate separate logs
                if issue['description'] and issue['conflicting_description']:
                    similarity = self.calculate_similarity(issue['description'], issue['conflicting_description'])
                    self.stdout.write(f"    Content similarity: {similarity:.1%}")
                    if similarity > 0.8:
                        self.stdout.write(f"    ⚠️  HIGH SIMILARITY - Likely duplicate content")
                    elif similarity < 0.3:
                        self.stdout.write(f"    ✅ LOW SIMILARITY - Likely different legitimate logs")
                self.stdout.write("-" * 80)
        else:
            self.stdout.write("✅ No BunkLog duplicate conflicts found")

    def analyze_counselorlog_duplicates(self):
        self.stdout.write(self.style.SUCCESS("\n📋 Analyzing CounselorLog potential duplicates..."))
        
        # Find records that would create duplicates if date is adjusted
        potential_issues = []
        
        for log in CounselorLog.objects.all().order_by('id'):
            created_date = timezone.localtime(log.created_at).date()
            
            # Only check records that need fixing (date mismatch)
            if log.date != created_date:
                # Check if adjusting this record would create a duplicate
                existing_with_new_date = CounselorLog.objects.filter(
                    counselor=log.counselor,
                    date=created_date
                ).exclude(id=log.id)
                
                if existing_with_new_date.exists():
                    try:
                        counselor_name = log.counselor.get_full_name() if hasattr(log.counselor, 'get_full_name') else str(log.counselor)
                    except:
                        counselor_name = "Unknown"
                        
                    conflicting_log = existing_with_new_date.first()
                    
                    potential_issues.append({
                        'log': log,
                        'counselor_name': counselor_name,
                        'current_date': log.date,
                        'target_date': created_date,
                        'conflicting_log': conflicting_log,
                        'elaboration': log.elaboration[:100] + '...' if len(log.elaboration) > 100 else log.elaboration,
                        'conflicting_elaboration': conflicting_log.elaboration[:100] + '...' if len(conflicting_log.elaboration) > 100 else conflicting_log.elaboration
                    })
        
        self.stdout.write(f"Found {len(potential_issues)} CounselorLog records that would create duplicates")
        
        if potential_issues:
            self.stdout.write("\n🚨 Potential duplicate conflicts:")
            self.stdout.write("=" * 100)
            
            for issue in potential_issues:
                self.stdout.write(f"\nID {issue['log'].id}: {issue['counselor_name']}")
                self.stdout.write(f"  Current date: {issue['current_date']} → Target date: {issue['target_date']}")
                self.stdout.write(f"  Elaboration: {issue['elaboration'] or 'No elaboration'}")
                self.stdout.write(f"  CONFLICTS WITH:")
                self.stdout.write(f"    ID {issue['conflicting_log'].id}: {issue['counselor_name']}")
                self.stdout.write(f"    Date: {issue['conflicting_log'].date}")
                self.stdout.write(f"    Elaboration: {issue['conflicting_elaboration'] or 'No elaboration'}")
                
                # Check if these might be actual duplicates or legitimate separate logs
                if issue['elaboration'] and issue['conflicting_elaboration']:
                    similarity = self.calculate_similarity(issue['elaboration'], issue['conflicting_elaboration'])
                    self.stdout.write(f"    Content similarity: {similarity:.1%}")
                    if similarity > 0.8:
                        self.stdout.write(f"    ⚠️  HIGH SIMILARITY - Likely duplicate content")
                    elif similarity < 0.3:
                        self.stdout.write(f"    ✅ LOW SIMILARITY - Likely different legitimate logs")
                self.stdout.write("-" * 80)
        else:
            self.stdout.write("✅ No CounselorLog duplicate conflicts found")

    def calculate_similarity(self, text1, text2):
        """Simple similarity calculation based on common words"""
        if not text1 or not text2:
            return 0.0
            
        # Clean and split into words
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
            
        # Calculate Jaccard similarity
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
