"""
Darwin Enterprise Evolve Beta — Trello Connector Service
Syncs Trello boards into the Neo4j knowledge graph.

Entity mapping:
  Board → System entity
  List → used as TEMPORAL edge metadata (sequencing)
  Card → Task entity
  Checklist Item → Requirement entity
  Label → Component entity
  Member → Person entity
  Comment → Decision entity
  Attachment → File entity

Edge types used:
  TEMPORAL — card in list (sequencing/status)
  AUTHORITY — card assigned to member
  INFORMATION — card has label, comment on card
  RESOURCE — attachment on card
  CONSTRAINT — checklist item blocks card completion
"""
import httpx
from datetime import datetime, timezone
from services.graph import (
    merge_entity, link_entity_to_room, create_relationship,
    set_entity_attribute, get_driver,
)

TRELLO_API_BASE = "https://api.trello.com/1"


def _trello_get(endpoint: str, api_key: str, token: str, params: dict = None) -> dict | list:
    """Make authenticated GET request to Trello API."""
    p = {"key": api_key, "token": token}
    if params:
        p.update(params)
    resp = httpx.get(f"{TRELLO_API_BASE}{endpoint}", params=p, timeout=30.0)
    resp.raise_for_status()
    return resp.json()


async def sync_trello_board(
    room_id: str,
    board_id: str,
    api_key: str,
    token: str,
    user_id: str,
) -> dict:
    """
    Sync a Trello board into the Neo4j graph.
    Returns summary of entities created.
    """
    stats = {
        "board": 0,
        "lists": 0,
        "cards": 0,
        "checklists": 0,
        "checklist_items": 0,
        "labels": 0,
        "members": 0,
        "comments": 0,
        "attachments": 0,
        "relationships": 0,
    }

    # --- 1. Fetch board ---
    board = _trello_get(f"/boards/{board_id}", api_key, token, {
        "fields": "name,desc,url,dateLastActivity",
    })
    board_entity_id = f"trello_board_{board_id}"
    merge_entity(board_entity_id, "System", board["name"], source="trello")
    set_entity_attribute(board_entity_id, "url", board.get("url", ""), "string", "trello")
    set_entity_attribute(board_entity_id, "description", board.get("desc", ""), "string", "trello")
    link_entity_to_room(board_entity_id, room_id)
    stats["board"] = 1

    # --- 2. Fetch lists ---
    lists = _trello_get(f"/boards/{board_id}/lists", api_key, token, {
        "fields": "name,pos,closed",
        "filter": "open",
    })
    list_map = {}
    for lst in lists:
        list_map[lst["id"]] = lst["name"]
        stats["lists"] += 1

    # --- 3. Fetch members ---
    members = _trello_get(f"/boards/{board_id}/members", api_key, token, {
        "fields": "fullName,username",
    })
    member_map = {}
    for member in members:
        member_entity_id = f"trello_member_{member['id']}"
        merge_entity(member_entity_id, "Person", member["fullName"], source="trello")
        set_entity_attribute(member_entity_id, "username", member.get("username", ""), "string", "trello")
        link_entity_to_room(member_entity_id, room_id)
        member_map[member["id"]] = member_entity_id
        stats["members"] += 1

    # --- 4. Fetch labels ---
    labels = _trello_get(f"/boards/{board_id}/labels", api_key, token, {
        "fields": "name,color",
    })
    label_map = {}
    for label in labels:
        if not label.get("name"):
            continue
        label_entity_id = f"trello_label_{label['id']}"
        merge_entity(label_entity_id, "Component", label["name"], source="trello")
        set_entity_attribute(label_entity_id, "color", label.get("color", ""), "string", "trello")
        link_entity_to_room(label_entity_id, room_id)
        label_map[label["id"]] = label_entity_id
        stats["labels"] += 1

    # --- 5. Fetch cards ---
    cards = _trello_get(f"/boards/{board_id}/cards", api_key, token, {
        "fields": "name,desc,idList,idMembers,idLabels,due,dateLastActivity,shortUrl,idChecklists",
        "filter": "open",
        "attachments": "true",
        "actions": "commentCard",
        "actions_limit": "50",
    })

    for card in cards:
        card_entity_id = f"trello_card_{card['id']}"
        merge_entity(card_entity_id, "Task", card["name"], source="trello")
        set_entity_attribute(card_entity_id, "description", card.get("desc", ""), "string", "trello")
        set_entity_attribute(card_entity_id, "url", card.get("shortUrl", ""), "string", "trello")
        if card.get("due"):
            set_entity_attribute(card_entity_id, "due_date", card["due"], "datetime", "trello")
        link_entity_to_room(card_entity_id, room_id)
        stats["cards"] += 1

        # Card → Board (INFORMATION)
        try:
            create_relationship(card_entity_id, board_entity_id, "BELONGS_TO", "INFORMATION")
            stats["relationships"] += 1
        except Exception:
            pass

        # Card in List → TEMPORAL edge with list name as status
        list_name = list_map.get(card.get("idList"), "Unknown")
        set_entity_attribute(card_entity_id, "status", list_name, "string", "trello")
        set_entity_attribute(card_entity_id, "list", list_name, "string", "trello")

        # Card → Members (AUTHORITY)
        for member_id in card.get("idMembers", []):
            if member_id in member_map:
                try:
                    create_relationship(card_entity_id, member_map[member_id], "ASSIGNED_TO", "AUTHORITY")
                    stats["relationships"] += 1
                except Exception:
                    pass

        # Card → Labels (INFORMATION)
        for label_id in card.get("idLabels", []):
            if label_id in label_map:
                try:
                    create_relationship(card_entity_id, label_map[label_id], "TAGGED_WITH", "INFORMATION")
                    stats["relationships"] += 1
                except Exception:
                    pass

        # Card → Attachments (RESOURCE)
        for attachment in card.get("attachments", []):
            att_entity_id = f"trello_attachment_{attachment['id']}"
            att_name = attachment.get("name", "Attachment")
            merge_entity(att_entity_id, "File", att_name, source="trello")
            set_entity_attribute(att_entity_id, "url", attachment.get("url", ""), "string", "trello")
            set_entity_attribute(att_entity_id, "mime_type", attachment.get("mimeType", ""), "string", "trello")
            link_entity_to_room(att_entity_id, room_id)
            try:
                create_relationship(card_entity_id, att_entity_id, "HAS_ATTACHMENT", "RESOURCE")
                stats["relationships"] += 1
            except Exception:
                pass
            stats["attachments"] += 1

        # Card → Comments as Decision entities (INFORMATION)
        for action in card.get("actions", []):
            if action.get("type") == "commentCard":
                comment_data = action.get("data", {}).get("text", "")
                if not comment_data:
                    continue
                comment_entity_id = f"trello_comment_{action['id']}"
                author_name = action.get("memberCreator", {}).get("fullName", "Unknown")
                merge_entity(comment_entity_id, "Decision", comment_data[:100], source="trello")
                set_entity_attribute(comment_entity_id, "content", comment_data, "string", "trello")
                set_entity_attribute(comment_entity_id, "author", author_name, "string", "trello")
                set_entity_attribute(comment_entity_id, "date", action.get("date", ""), "datetime", "trello")
                link_entity_to_room(comment_entity_id, room_id)
                try:
                    create_relationship(comment_entity_id, card_entity_id, "COMMENTS_ON", "INFORMATION")
                    stats["relationships"] += 1
                except Exception:
                    pass
                stats["comments"] += 1

    # --- 6. Fetch checklists ---
    for card in cards:
        for checklist_id in card.get("idChecklists", []):
            try:
                checklist = _trello_get(f"/checklists/{checklist_id}", api_key, token, {
                    "fields": "name",
                    "checkItems": "all",
                    "checkItem_fields": "name,state",
                })
                stats["checklists"] += 1
                card_entity_id = f"trello_card_{card['id']}"

                for item in checklist.get("checkItems", []):
                    item_entity_id = f"trello_checkitem_{item['id']}"
                    merge_entity(item_entity_id, "Requirement", item["name"], source="trello")
                    set_entity_attribute(item_entity_id, "status", item.get("state", "incomplete"), "string", "trello")
                    set_entity_attribute(item_entity_id, "checklist", checklist.get("name", ""), "string", "trello")
                    link_entity_to_room(item_entity_id, room_id)
                    try:
                        create_relationship(item_entity_id, card_entity_id, "REQUIRED_BY", "CONSTRAINT")
                        stats["relationships"] += 1
                    except Exception:
                        pass
                    stats["checklist_items"] += 1

            except Exception:
                continue

    return {
        "board": board["name"],
        "board_id": board_id,
        "stats": stats,
        "total_entities": stats["board"] + stats["cards"] + stats["checklist_items"] + stats["labels"] + stats["members"] + stats["comments"] + stats["attachments"],
        "total_relationships": stats["relationships"],
    }
