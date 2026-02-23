"""
Darwin Enterprise Evolve Beta — Figma Connector
Fetches file structure, pages, and components from Figma.
Writes them as Entity nodes in Neo4j with five-edge-type relationships.
"""
import httpx
from services.graph import merge_entity, set_entity_attribute, create_relationship, link_entity_to_room
from services.audit import audit

FIGMA_API = "https://api.figma.com/v1"


async def sync_figma_file(
    room_id: str,
    file_key: str,
    token: str,
    user_id: str,
) -> dict:
    """
    Sync a Figma file into the graph.
    file_key: the key from the Figma URL (e.g., "abc123" from figma.com/file/abc123/...)
    token: Figma personal access token
    Returns: summary of what was synced
    """
    headers = {
        "X-Figma-Token": token,
    }

    summary = {"pages": 0, "frames": 0, "components": 0, "errors": []}

    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        # --- Get file metadata ---
        try:
            resp = await client.get(f"{FIGMA_API}/files/{file_key}", params={"depth": 2})
            if resp.status_code != 200:
                summary["errors"].append(f"File fetch: {resp.status_code} {resp.text[:200]}")
                return summary

            file_data = resp.json()
        except Exception as e:
            summary["errors"].append(f"File fetch: {str(e)}")
            return summary

        file_name = file_data.get("name", file_key)
        last_modified = file_data.get("lastModified", "")

        # --- Create file entity ---
        file_entity_id = f"figma_file_{file_key}"
        merge_entity(file_entity_id, "FigmaFile", file_name, source="figma")
        set_entity_attribute(file_entity_id, "url", f"https://www.figma.com/file/{file_key}", "string", "figma")
        set_entity_attribute(file_entity_id, "file_key", file_key, "string", "figma")
        set_entity_attribute(file_entity_id, "last_modified", last_modified, "datetime", "figma")
        set_entity_attribute(file_entity_id, "platform", "figma", "string", "figma")
        link_entity_to_room(file_entity_id, room_id)

        # --- Walk the document tree ---
        document = file_data.get("document", {})
        children = document.get("children", [])

        for page in children:
            page_id = f"figma_page_{file_key}_{page['id'].replace(':', '_')}"
            page_name = page.get("name", "Untitled Page")

            merge_entity(page_id, "FigmaPage", page_name, source="figma")
            set_entity_attribute(page_id, "figma_id", page["id"], "string", "figma")

            try:
                create_relationship(page_id, file_entity_id, "PAGE_OF", "INFORMATION")
            except Exception:
                pass

            link_entity_to_room(page_id, room_id)
            summary["pages"] += 1

            # Get frames and components within each page
            for child in page.get("children", []):
                child_type = child.get("type", "")

                if child_type == "FRAME":
                    frame_id = f"figma_frame_{file_key}_{child['id'].replace(':', '_')}"
                    frame_name = child.get("name", "Untitled Frame")

                    merge_entity(frame_id, "FigmaFrame", frame_name, source="figma")
                    set_entity_attribute(frame_id, "figma_id", child["id"], "string", "figma")
                    set_entity_attribute(frame_id, "frame_type", child_type, "string", "figma")

                    try:
                        create_relationship(frame_id, page_id, "IN_PAGE", "INFORMATION")
                    except Exception:
                        pass

                    link_entity_to_room(frame_id, room_id)
                    summary["frames"] += 1

                elif child_type == "COMPONENT" or child_type == "COMPONENT_SET":
                    comp_id = f"figma_comp_{file_key}_{child['id'].replace(':', '_')}"
                    comp_name = child.get("name", "Untitled Component")

                    merge_entity(comp_id, "FigmaComponent", comp_name, source="figma")
                    set_entity_attribute(comp_id, "figma_id", child["id"], "string", "figma")
                    set_entity_attribute(comp_id, "component_type", child_type, "string", "figma")

                    try:
                        create_relationship(comp_id, page_id, "IN_PAGE", "INFORMATION")
                    except Exception:
                        pass

                    link_entity_to_room(comp_id, room_id)
                    summary["components"] += 1

        # --- Get file versions for drift detection ---
        try:
            resp = await client.get(f"{FIGMA_API}/files/{file_key}/versions", params={"page_size": 5})
            if resp.status_code == 200:
                versions = resp.json().get("versions", [])
                if versions:
                    latest = versions[0]
                    set_entity_attribute(file_entity_id, "latest_version_label", latest.get("label", ""), "string", "figma")
                    set_entity_attribute(file_entity_id, "latest_version_date", latest.get("created_at", ""), "datetime", "figma")
                    set_entity_attribute(file_entity_id, "latest_version_user", latest.get("user", {}).get("handle", ""), "string", "figma")
        except Exception:
            pass

    # Audit
    audit(user_id, "connector_synced", room_id, "figma", file_entity_id, {
        "file_key": file_key,
        "file_name": file_name,
        "pages": summary["pages"],
        "frames": summary["frames"],
        "components": summary["components"],
    })

    return summary
