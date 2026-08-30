import json
import logging
import re
from typing import Generator
from flask import current_app
from google import genai
from google.genai import types
from google.genai.errors import ClientError, APIError, ServerError
from app import db
from app.models import Message, Order, Chat
from app.services.usage import calculate_cost
from app.services.rag import retrieve

logger = logging.getLogger(__name__)

PRODUCT_CATALOG = {
    'ETHIOP-YRGA-12': {'name': 'Ethiopian Yirgacheffe', 'weight': '12oz', 'price': 18.50, 'notes': 'Bright, floral & bergamot'},
    'COLOM-HUILA-12': {'name': 'Colombian Huila', 'weight': '12oz', 'price': 16.00, 'notes': 'Chocolate, caramel & sweet citrus'},
    'GUATE-ANTI-12':  {'name': 'Guatemala Antigua', 'weight': '12oz', 'price': 17.50, 'notes': 'Rich cocoa & warm spice'},
    'BLEND-HOUSE-12': {'name': 'House Blend', 'weight': '12oz', 'price': 14.00, 'notes': 'Balanced, sweet & smooth daily roast'},
    'BLEND-DARK-12':  {'name': 'Dark Roast Blend', 'weight': '12oz', 'price': 14.50, 'notes': 'Deep, smoky & dark molasses'},
}


def _build_context_and_prompt(user_id: int, chat_id: int, user_message: str):
    chat = db.session.get(Chat, chat_id)
    if not chat:
        return None, None, None, None

    if not chat.title or chat.title in ['New chat', 'New Chat', 'New Conversation']:
        chat.title = user_message[:45].strip()
        db.session.commit()

    tool_calls_record = []

    # 1. RAG Knowledge Base Retrieval
    retrieved_chunks = retrieve(user_message, top_k=3, score_threshold=0.80)
    if retrieved_chunks:
        tool_calls_record.append({
            "name": "search_knowledge_base",
            "args": {"query": user_message, "chunks_found": len(retrieved_chunks)}
        })
        rag_context = "\n=== ROAST & CO. OFFICIAL KNOWLEDGE BASE (RAG) ===\n" + "\n---\n".join(retrieved_chunks)
    else:
        rag_context = "\n=== ROAST & CO. OFFICIAL KNOWLEDGE BASE (RAG) ===\n(No matching FAQ policy documents found above 0.80 similarity threshold. Answer politely that Roast & Co. does not have this specific policy on file.)"

    # 2. User Scoped Order Data
    user_orders = Order.query.filter_by(user_id=user_id).order_by(Order.id.desc()).limit(8).all()
    orders_context = "\n=== CUSTOMER'S ACTIVE & RECENT ORDERS ===\n"
    if user_orders:
        for o in user_orders:
            items_str = ", ".join([f"{it.get('qty', 1)}x {it.get('name', it.get('sku'))}" for it in (o.items or [])])
            orders_context += f"- Order #{o.id}: Status='{o.status}', Items=[{items_str}], Address='{o.address}', Placed='{o.created_at.strftime('%Y-%m-%d') if o.created_at else 'Recent'}'\n"
    else:
        orders_context += "The customer currently has no past orders.\n"

    # 3. Handle Order Cancellation / Creation intent directly if confirmed in text
    msg_lower = user_message.lower()

    cancel_match = re.search(r'(?:cancel|terminate)\s+order\s*#?\s*(\d+)', msg_lower)
    if cancel_match:
        target_oid = int(cancel_match.group(1))
        target_order = Order.query.filter_by(id=target_oid, user_id=user_id).first()
        if target_order and target_order.status == 'placed':
            target_order.status = 'cancelled'
            db.session.commit()
            tool_calls_record.append({"name": "cancel_order", "args": {"order_id": target_oid, "status": "cancelled"}})
            orders_context += f"\n[SYSTEM UPDATE]: Order #{target_oid} has just been CANCELLED upon customer request.\n"

    # Order creation intent
    for sku, pinfo in PRODUCT_CATALOG.items():
        if sku.lower() in msg_lower or pinfo['name'].lower() in msg_lower:
            if any(kw in msg_lower for kw in ['street', 'st', 'ave', 'road', 'rd', 'shipping to', 'deliver to', 'address']):
                qty_match = re.search(r'(\d+)\s*(?:bag|bags|pack|packs|x)?', msg_lower)
                qty = int(qty_match.group(1)) if qty_match else 1
                
                addr_match = re.search(r'(?:to|address:?)\s+([^.\n]+)', user_message, re.IGNORECASE)
                addr = addr_match.group(1).strip() if addr_match else user_message
                
                new_order = Order(
                    user_id=user_id,
                    items=[{'sku': sku, 'name': pinfo['name'], 'qty': qty, 'price': pinfo['price']}],
                    address=addr,
                    status='placed'
                )
                db.session.add(new_order)
                db.session.commit()
                tool_calls_record.append({"name": "create_order", "args": {"sku": sku, "qty": qty, "order_id": new_order.id, "address": addr}})
                orders_context += f"\n[SYSTEM UPDATE]: Order #{new_order.id} for {qty}x {pinfo['name']} has just been PLACED and shipping to '{addr}'.\n"
                break

    # 4. Multi-turn conversation context
    past_msgs = Message.query.filter_by(chat_id=chat_id).order_by(Message.created_at.desc()).limit(8).all()
    past_msgs.reverse()
    history_transcript = ""
    for m in past_msgs:
        history_transcript += f"{m.role.capitalize()}: {m.content}\n"

    catalog_summary = "\n".join([f"- {info['name']} (SKU: {s}, 12oz) - ${info['price']:.2f} ({info['notes']})" for s, info in PRODUCT_CATALOG.items()])

    system_instruction = f"""You are the Roast & Co. specialty coffee roastery assistant.
Your tone is warm, artisanal, knowledgeable, and concise.

Roast & Co. Coffee Catalog:
{catalog_summary}

{orders_context}
{rag_context}

Behavior Guidelines:
1. FAQ Questions: Answer customer inquiries about shipping times, shipping rates, return policy, and coffee brewing methods using the official knowledge base context above. If the information is not in the knowledge base, state politely that you don't have that information on file.
2. Orders: When customers inquire about orders, tracking, or cancellations, refer to their order history above accurately.
3. Placing Orders: When a customer orders or confirms coffee, celebrate their choice and confirm the placed order details. If details (coffee name/SKU or shipping address) are missing, guide them with available coffee options and request the shipping address.
4. Always provide grounded, authentic specialty roastery assistance. Keep replies beautifully formatted in markdown.
"""

    full_prompt = f"""Conversation History:
{history_transcript}
Customer: {user_message}
Assistant:"""

    return chat, system_instruction, full_prompt, tool_calls_record


def stream_message(user_id: int, chat_id: int, user_message: str) -> Generator[str, None, None]:
    """
    Streams the AI response tokens via Server-Sent Events (SSE).
    """
    chat, system_instruction, full_prompt, tool_calls_record = _build_context_and_prompt(user_id, chat_id, user_message)
    if not chat:
        yield f"data: {json.dumps({'error': 'Chat not found'})}\n\n"
        return

    client = genai.Client(api_key=current_app.config['GEMINI_API_KEY'])
    primary_model = current_app.config.get('GEMINI_MODEL', 'gemini-3.6-flash')
    fallback_models = current_app.config.get('FALLBACK_MODELS', ['gemini-3.6-flash', 'gemini-3.5-flash', 'gemini-3.5-flash-lite', 'gemini-3.1-flash-lite'])
    candidate_models = [primary_model] + [m for m in fallback_models if m != primary_model]

    stream = None
    last_err = None

    for model_candidate in candidate_models:
        try:
            stream = client.models.generate_content_stream(
                model=model_candidate,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.3
                )
            )
            break
        except Exception as e:
            last_err = e
            logger.warning(f"Streaming failed with model '{model_candidate}': {e}. Falling back...")
            continue

    if not stream:
        err_msg = "I am currently receiving high traffic. Please try again in a few moments."
        yield f"data: {json.dumps({'chunk': err_msg})}\n\n"
        yield f"data: {json.dumps({'done': True, 'chat_title': chat.title})}\n\n"
        return

    full_response_text = ""
    prompt_tokens = 0
    completion_tokens = 0

    try:
        for chunk in stream:
            if chunk.text:
                full_response_text += chunk.text
                yield f"data: {json.dumps({'chunk': chunk.text})}\n\n"
            if chunk.usage_metadata:
                prompt_tokens = chunk.usage_metadata.prompt_token_count or prompt_tokens
                completion_tokens = chunk.usage_metadata.candidates_token_count or completion_tokens

        # Fallback token estimation if metadata omitted
        if prompt_tokens == 0:
            prompt_tokens = max(1, len(full_prompt.split()))
        if completion_tokens == 0:
            completion_tokens = max(1, len(full_response_text.split()))

        cost = calculate_cost(prompt_tokens, completion_tokens)

        # Persist messages to DB
        user_msg_obj = Message(chat_id=chat_id, role='user', content=user_message)
        db.session.add(user_msg_obj)

        assistant_msg_obj = Message(
            chat_id=chat_id,
            role='assistant',
            content=full_response_text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost,
            tool_calls=json.dumps(tool_calls_record) if tool_calls_record else None
        )
        db.session.add(assistant_msg_obj)
        db.session.commit()

        yield f"data: {json.dumps({'done': True, 'chat_title': chat.title, 'cost_usd': float(cost)})}\n\n"

    except Exception as e:
        logger.error(f"Error during stream consumption: {e}", exc_info=True)
        fallback_msg = " (Connection interrupted. Please try again.)"
        yield f"data: {json.dumps({'chunk': fallback_msg})}\n\n"
        yield f"data: {json.dumps({'done': True, 'chat_title': chat.title})}\n\n"


def process_message(user_id: int, chat_id: int, user_message: str) -> str:
    """
    Synchronous fallback for testing or non-streaming requests.
    """
    chat, system_instruction, full_prompt, tool_calls_record = _build_context_and_prompt(user_id, chat_id, user_message)
    if not chat:
        return "Error: Chat not found."

    client = genai.Client(api_key=current_app.config['GEMINI_API_KEY'])
    model_name = current_app.config.get('GEMINI_MODEL', 'gemini-3.6-flash')

    response = client.models.generate_content(
        model=model_name,
        contents=full_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.3
        )
    )

    prompt_tokens = response.usage_metadata.prompt_token_count if response.usage_metadata else 0
    completion_tokens = response.usage_metadata.candidates_token_count if response.usage_metadata else 0
    final_text = response.text or "Welcome to Roast & Co.!"
    cost = calculate_cost(prompt_tokens, completion_tokens)

    user_msg_obj = Message(chat_id=chat_id, role='user', content=user_message)
    db.session.add(user_msg_obj)

    assistant_msg_obj = Message(
        chat_id=chat_id,
        role='assistant',
        content=final_text,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost_usd=cost,
        tool_calls=json.dumps(tool_calls_record) if tool_calls_record else None
    )
    db.session.add(assistant_msg_obj)
    db.session.commit()

    return final_text
