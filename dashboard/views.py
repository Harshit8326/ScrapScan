from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from .models import DigitalPassport
import random
import uuid # This helps us generate unique Item IDs
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Avg, Count
import yfinance as yf
import google.generativeai as genai
import json
from PIL import Image
import csv
from django.http import HttpResponse
from decimal import Decimal
# Paste your actual key here!
genai.configure(api_key="AIzaSyA35c81g2211U3Nu7yqsxlkwpE3io_U9bk")

@login_required(login_url='/login/')
def operator_view(request):
    return render(request, 'dashboard/operator.html')

def get_live_scrap_rate():
    try:
        # 1. Fetch live Cotton #2 futures (Ticker: CT=F) from the global market
        cotton_data = yf.Ticker("CT=F")
        live_cents_per_lb = cotton_data.history(period="1d")['Close'].iloc[-1]
        
        # 2. Convert Cents/lb to USD/kg, then to INR/kg (1 lb = 0.453 kg, $1 = ~₹83)
        price_usd_per_kg = (live_cents_per_lb / 100) / 0.453
        price_inr_per_kg = price_usd_per_kg * 83
        
        # 3. High-quality textile scrap trades at roughly 30% of the price of raw virgin cotton
        scrap_rate_inr = price_inr_per_kg * 0.30
        
        return round(scrap_rate_inr, 2)
    except Exception as e:
        print(f"Finance API Error: {e}")
        # Safe fallback rate of ₹40/kg just in case the stock market API is down during your presentation!
        return 40.00
@csrf_exempt
def process_scan(request):
    if request.method == 'POST' and request.FILES.get('image'):
        try:
            # 1. Grab the uploaded image
            uploaded_file = request.FILES['image']
            image = Image.open(uploaded_file)
            
            # 2. Load the Gemini Vision model
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            # 3. Give Gemini very strict instructions
            prompt = """
            You are an expert AI sorting system for a textile recycling plant. 
            Look at this image of fabric scrap. 
            Return ONLY a valid, raw JSON object (no markdown, no code blocks, no backticks).
            It must have exactly these keys:
            - "material" (string: guess either 'Denim', 'Cotton', 'Polyester', or 'Mixed Blend')
            - "confidence" (integer: 0 to 100 representing how sure you are)
            - "buttons" (integer: count of any buttons visible, 0 if none)
            - "zippers" (integer: count of any zippers visible, 0 if none)
            """
            
            # 4. Send the image and prompt to Gemini
            response = model.generate_content([prompt, image])
            
            # 5. Clean up the response and turn it into a Python dictionary
            raw_text = response.text.strip().replace('```json', '').replace('```', '')
            ai_data = json.loads(raw_text)
            
            material = ai_data.get('material', 'Unknown')
            confidence = ai_data.get('confidence', 85)
            buttons = ai_data.get('buttons', 0)
            zippers = ai_data.get('zippers', 0)

            # --- THE MISSING PIECE: SAVE TO DATABASE ---
            # Generate a random weight and calculate a mock price based on the AI's confidence
            generated_weight = round(random.uniform(5.0, 50.0), 2)
            live_base_rate = get_live_scrap_rate()
            calculated_price = round(generated_weight * (confidence / 100) * live_base_rate, 2)
            
            # Create the pending Digital Twin!
            # --- UPDATE: SAVE DRAFT TO DATABASE ---
            # We set weight and price to 0 initially, waiting for the operator!
            new_twin = DigitalPassport.objects.create(
                item_id=f"TX-2026-{str(uuid.uuid4())[:8].upper()}",
                operator=request.user,
                primary_material=material,
                purity_score=confidence,
                button_count=buttons,
                zipper_count=zippers,
                weight=0.0,
                price=0.0,
                status='pending'
            )
            # -------------------------------------------
            
            # 6. Send the AI data AND the new database ID back to the frontend
            return JsonResponse({
                'status': 'success',
                'db_id': new_twin.id,  # <--- We need this to attach the weight later!
                'material': material,
                'confidence': confidence,
                'buttons': buttons,
                'zippers': zippers
            })
            
        except Exception as e:
            print(f"AI Error: {e}")
            return JsonResponse({
                'status': 'success', 
                'material': 'Error Reading Image',
                'confidence': 0,
                'buttons': 0,
                'zippers': 0
            })

    return JsonResponse({'status': 'error', 'message': 'No image provided'}, status=400)
def marketplace_view(request):
    # Fetch all items that have been verified, ordered by newest first
    available_items = DigitalPassport.objects.filter(status='verified').order_by('-timestamp')
    
    # Pass the items to the frontend template
    return render(request, 'dashboard/marketplace.html', {'items': available_items})

@login_required(login_url='/login/')
def digital_thread_view(request):
    # Fetch all items that are waiting to be verified
    pending_items = DigitalPassport.objects.filter(status='pending').order_by('-timestamp')
    
    return render(request, 'dashboard/thread.html', {'items': pending_items})
def verify_item(request, item_id):
    if request.method == 'POST':
        try:
            item = DigitalPassport.objects.get(id=item_id)
            
            # Read the incoming edited JSON from the frontend
            data = json.loads(request.body)
            
            # Extract the potentially edited contaminant counts
            # (Using .get() safely navigates the JSON structure)
            edited_buttons = data.get('contaminants', [{}])[0].get('count', item.button_count)
            edited_zippers = data.get('contaminants', [{}, {}])[1].get('count', item.zipper_count)
            
            # Update the database record with the operator's manual overrides
            item.button_count = int(edited_buttons)
            item.zipper_count = int(edited_zippers)
            
            # Finally, mark it as verified
            item.status = 'verified'
            item.save()
            
            return JsonResponse({'status': 'success'})
            
        except DigitalPassport.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Item not found'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Corrupted JSON data received'}, status=400)
            
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)
# --- AUTHENTICATION VIEWS ---

def signup_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user) # Automatically log them in after signup
            return redirect('operator_view')
    else:
        form = UserCreationForm()
    return render(request, 'dashboard/signup.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('operator_view')
    else:
        form = AuthenticationForm()
    return render(request, 'dashboard/login.html', {'form': form})

def logout_view(request):
    if request.method == 'POST':
        logout(request)
        return redirect('login_view')
    
def digital_twin_detail(request, item_id):
    # Look up the specific item by its unique ID (e.g., TX-2026-ABCD)
    item = get_object_or_404(DigitalPassport, item_id=item_id)
    return render(request, 'dashboard/twin_detail.html', {'item': item})

@login_required(login_url='/login/')
def analytics_dashboard_view(request):
    # 1. Calculate Top-Level KPIs
    total_scans = DigitalPassport.objects.count()
    
    # Sum the weight of only VERIFIED items (returns a dictionary, so we grab the value)
    weight_dict = DigitalPassport.objects.filter(status='verified').aggregate(Sum('weight'))
    total_weight = weight_dict['weight__sum'] or 0 # Default to 0 if database is empty
    
    # Average the purity score of all items
    purity_dict = DigitalPassport.objects.aggregate(Avg('purity_score'))
    avg_purity = purity_dict['purity_score__avg'] or 0

    # 2. Gather data for the Chart (Count items by Material Type)
    material_data = DigitalPassport.objects.values('primary_material').annotate(count=Count('id'))
    
    # Format the data for Chart.js
    materials = [item['primary_material'] for item in material_data]
    counts = [item['count'] for item in material_data]

    context = {
        'total_scans': total_scans,
        'total_weight': round(total_weight, 1),
        'avg_purity': round(avg_purity, 1),
        'materials_json': json.dumps(materials), # Converts Python list to JS-readable format
        'counts_json': json.dumps(counts),
    }
    
    return render(request, 'dashboard/analytics.html', context)

@csrf_exempt
def group_items_api(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        item_ids = data.get('ids', [])
        
        # Generate a unique Batch ID for the whole group
        new_batch_id = f"LOT-{str(uuid.uuid4())[:6].upper()}"
        
        # Update all selected items
        DigitalPassport.objects.filter(id__in=item_ids).update(batch_group_id=new_batch_id)
        
        return JsonResponse({'status': 'success', 'batch_id': new_batch_id})
    return JsonResponse({'status': 'error'}, status=400)


@csrf_exempt
def purchase_item_api(request, item_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # 1. Grab the item from the DB
            item = DigitalPassport.objects.get(item_id=item_id)
            
            # 2. Detach everything into strict Decimals (using strings to prevent float leak)
            req_w = Decimal(str(data.get('weight', 0)))
            curr_w = Decimal(str(item.weight))
            curr_p = Decimal(str(item.price))
            
            # Security Check
            if req_w <= Decimal('0') or req_w > curr_w:
                return JsonResponse({'status': 'error', 'message': 'Invalid weight requested'}, status=400)
            
            # Scenario A: Full Purchase
            if req_w == curr_w:
                item.status = 'sold'
                item.save()
                
            # Scenario B: Partial Purchase (Safe, detached math)
            else:
                # Do the math in the air, away from Django's database rules
                price_per_kg = curr_p / curr_w
                new_w = curr_w - req_w
                new_p = new_w * price_per_kg
                
                # Now that the math is done, assign it safely back to the item
                item.weight = round(new_w, 2)
                item.price = round(new_p, 2)
                item.save()
            
            mock_tx_hash = f"0x{str(uuid.uuid4()).replace('-', '')}"
            
            return JsonResponse({
                'status': 'success', 
                'tx_hash': mock_tx_hash,
                'remaining_weight': float(item.weight) 
            })
            
        except DigitalPassport.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Item not found'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
            
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)
@login_required(login_url='/login/')
def export_compliance_csv(request):
    # 1. Tell the browser we are sending a CSV file, not a webpage
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="scrapscan_compliance_report.csv"'

    # 2. Create a CSV writer
    writer = csv.writer(response)

    # 3. Write the Header Row
    writer.writerow(['Item ID', 'Operator', 'Material', 'Weight (kg)', 'Purity (%)', 'Buttons', 'Zippers', 'Status', 'Scan Date'])

    # 4. Fetch all data from the database and write the rows
    items = DigitalPassport.objects.all().order_by('-timestamp')
    for item in items:
        writer.writerow([
            item.item_id,
            item.operator.username if item.operator else 'System',
            item.primary_material,
            item.weight,
            item.purity_score,
            item.button_count,
            item.zipper_count,
            item.status.upper(),
            item.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        ])

    return response

@csrf_exempt
def add_weight_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            twin_id = data.get('db_id')
            actual_weight = float(data.get('weight'))
            
            # 1. Find that draft twin in the database
            twin = DigitalPassport.objects.get(id=twin_id)
            
            # 2. Calculate the real price using your live finance API!
            live_base_rate = get_live_scrap_rate()
            final_price = round(actual_weight * (twin.purity_score / 100) * live_base_rate, 2)
            
            # 3. Update the twin and permanently save it
            twin.weight = actual_weight
            twin.price = final_price
            twin.save()
            
            return JsonResponse({'status': 'success', 'final_price': final_price})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)