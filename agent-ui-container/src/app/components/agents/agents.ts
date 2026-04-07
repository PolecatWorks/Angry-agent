import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ChatService, AgentDefinition } from '../../services/chat.service';

@Component({
    selector: 'app-agents',
    standalone: true,
    imports: [CommonModule, FormsModule],
    templateUrl: './agents.html'
})
export class AgentsComponent implements OnInit {
    agents: AgentDefinition[] = [];
    loading = true;
    error: string | null = null;

    selectedAgent: AgentDefinition | null = null;
    isEditing = false;

    constructor(private chatService: ChatService) {}

    ngOnInit() {
        this.loadAgents();
    }

    loadAgents() {
        this.loading = true;
        this.chatService.getAgents().subscribe({
            next: (res) => {
                this.agents = res;
                this.loading = false;
            },
            error: (err) => {
                console.error('Failed to load agents', err);
                this.error = 'Failed to load agents.';
                this.loading = false;
            }
        });
    }

    selectAgent(agent: AgentDefinition) {
        // Clone for editing
        this.selectedAgent = { ...agent };
        this.isEditing = true;
    }

    newAgent() {
        this.selectedAgent = { name: '', content: '' };
        this.isEditing = true;
    }

    cancelEdit() {
        this.selectedAgent = null;
        this.isEditing = false;
    }

    saveAgent() {
        if (!this.selectedAgent || !this.selectedAgent.name || !this.selectedAgent.content) {
            return;
        }

        const action = this.selectedAgent.id
            ? this.chatService.updateAgent(this.selectedAgent.id, this.selectedAgent)
            : this.chatService.createAgent(this.selectedAgent);

        action.subscribe({
            next: () => {
                this.loadAgents();
                this.cancelEdit();
            },
            error: (err) => {
                console.error('Failed to save agent', err);
                this.error = 'Failed to save agent.';
            }
        });
    }

    deleteAgent(id: string | undefined, event: Event) {
        event.stopPropagation();
        if (!id || !confirm('Are you sure you want to delete this agent?')) return;

        this.chatService.deleteAgent(id).subscribe({
            next: () => {
                if (this.selectedAgent?.id === id) {
                    this.cancelEdit();
                }
                this.loadAgents();
            },
            error: (err) => {
                console.error('Failed to delete agent', err);
                this.error = 'Failed to delete agent.';
            }
        });
    }
}
