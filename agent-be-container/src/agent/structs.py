import operator
import uuid
from typing import Annotated, List, Literal, Any, Dict
from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

def visualizations_reducer(existing: List['MFEContent'], new: List[Dict[str, Any]] | Dict[str, Any]) -> List['MFEContent']:
    """Reducer for managing the visualizations state list.

    Expects new to be a list of commands or a single command dict, e.g.:
    {"action": "add", "id": "...", ...}   -> appends to the end
    {"action": "update", "id": "...", ...} -> updates in place, or moves if 'index' or 'order_index' is set
    {"action": "delete", "id": "..."}      -> removes from the list
    {"action": "reorder", "ids": [...]}    -> reorders existing items by their IDs
    {"action": "replace", "visualizations": [...]} -> replaces the entire list
    """
    if existing is None:
        existing = []

    # If the new payload is a single dict, wrap it in a list to normalize
    if isinstance(new, dict):
        new_items = [new]
    elif isinstance(new, list):
        new_items = new
    else:
        return existing

    # Create a shadow copy of the list to work with
    current_list = list(existing)

    def find_index(id_: str) -> int | None:
        for i, item in enumerate(current_list):
            if item.id == id_:
                return i
        return None

    for item in new_items:
        if not isinstance(item, dict):
            continue

        action = item.get("action", "update")

        if action == "add":
            # Add new item. Filter out action key before validation.
            content_data = {k: v for k, v in item.items() if k != "action"}
            try:
                mfe_obj = MFEContent.model_validate(content_data)
                current_list.append(mfe_obj)
            except Exception:
                pass

        elif action == "update":
            viz_id = item.get("id")
            if not viz_id:
                continue
            idx = find_index(viz_id)
            if idx is not None:
                # Update item data
                current_data = current_list[idx].model_dump()
                # Merging (excluding action and positional keys)
                for k, v in item.items():
                    if k not in ("action", "order_index", "index"):
                        current_data[k] = v

                try:
                    updated_obj = MFEContent.model_validate(current_data)

                    # Handle reordering if requested in the update
                    new_pos = item.get("order_index") if item.get("order_index") is not None else item.get("index")
                    if new_pos is not None:
                        current_list.pop(idx)
                        # Clamp position
                        target = max(0, min(int(new_pos), len(current_list)))
                        current_list.insert(target, updated_obj)
                    else:
                        current_list[idx] = updated_obj
                except Exception:
                    pass

        elif action == "delete":
            viz_id = item.get("id")
            if viz_id:
                idx = find_index(viz_id)
                if idx is not None:
                    current_list.pop(idx)

        elif action == "reorder":
            # Item has an 'ids' list. Reorder existing based on those IDs.
            # Only keeps items present in 'ids'.
            order_ids = item.get("ids", [])
            viz_map = {v.id: v for v in current_list if v.id}
            reordered = []
            for oid in order_ids:
                if oid in viz_map:
                    reordered.append(viz_map[oid])
            # Keep anything NOT in the ids list at the end? (Optional logic)
            # For now, strictly follow the order defined in 'ids'.
            current_list = reordered

        elif action == "replace":
            # Completely replace list
            current_list = item.get("visualizations", [])

    return current_list


class MFEBase(BaseModel):
    name: str = Field(description="A unique name for the visual element")
    title: str = Field(description="The title of the visual element")
    description: str = Field(description="A description for the visual element")

class MFEContent(MFEBase):
    provider: str = Field(description="The MFE provider that will render the component (e.g. 'mfe1'). This MUST be taken verbatim from the tool results")
    component: str = Field(description="The name of the MFE component to use for rendering. This MUST be taken verbatim from the tool results.")
    content: Any = Field(description="The content to render in the MFE. This MUST be taken verbatim from the tool results.")
    id: str = Field(default_factory=lambda: uuid.uuid4().hex, description="The ID of the visualization from the database, if it's pinned to the pane.")



class MFEContainer(BaseModel):
    """The final response object containing all Micro-Frontend components."""
    mfes: List[MFEContent] = Field(description="A list of MFE components to render in the UI")


class PromptFeedback(BaseModel):
    """Feedback on the user's prompt when learning mode is enabled."""
    feedback_text: str = Field(description="Feedback on why the prompt is good or bad, and how it could be improved.")
    improved_prompt: str = Field(description="A highly improved, more specific and context-rich version of the original prompt.")
    alternatives: List[str] = Field(description="A list of 1-3 alternative ways to ask the question.")


class FollowUpQuestions(BaseModel):
    """Suggested follow-up questions for the user to ask the AI agent based on the conversation history."""
    follow_up_questions: List[str] = Field(description="Exactly 3 highly contextual and relevant follow-up questions the user could ask next.")


class AgentState(BaseModel):
    messages: Annotated[List[BaseMessage], add_messages] = Field(default_factory=list)
    visualizations: Annotated[List[MFEContent], visualizations_reducer] = Field(default_factory=list)
