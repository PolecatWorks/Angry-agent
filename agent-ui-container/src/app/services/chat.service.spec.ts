import { ChatService, Thread, ChatResponse, HistoryResponse } from './chat.service';
import { of } from 'rxjs';
import { vi } from 'vitest';

describe('ChatService', () => {
    let service: ChatService;
    let httpClientSpy: any;
    let authServiceSpy: any;

    beforeEach(() => {
        httpClientSpy = {
            post: vi.fn(),
            get: vi.fn(),
            delete: vi.fn()
        };
        authServiceSpy = {
            getUserId: vi.fn().mockReturnValue('test-user'),
            isLoggedIn: vi.fn()
        };

        service = new ChatService(httpClientSpy, authServiceSpy);
    });

    it('should be created', () => {
        expect(service).toBeTruthy();
    });

    it('should refresh threads', () => {
        const mockThreads: Thread[] = [{ thread_id: '1', user_id: 'u', title: 't' }];
        httpClientSpy.get.mockReturnValue(of({ threads: mockThreads }));

        let threads: Thread[] = [];
        service.threads$.subscribe(t => threads = t);

        service.refreshThreads();

        expect(threads).toEqual(mockThreads);
    });

    it('should send a message and return response', () => {
        const mockResponse: ChatResponse = { thread_id: 'thread-1', response: 'Hello user' };
        const message = 'Hello';

        httpClientSpy.post.mockReturnValue(of(mockResponse));

        service.sendMessage(message).subscribe(response => {
            expect(response).toEqual(mockResponse);
        });

        expect(httpClientSpy.post).toHaveBeenCalledWith(
            expect.stringContaining('/api/chat'),
            expect.objectContaining({ message, thread_id: undefined }),
            expect.anything() // headers
        );
    });

    it('should send a message with threadId', () => {
        const mockResponse: ChatResponse = { thread_id: 'thread-1', response: 'Hello again' };
        const message = 'How are you?';
        const threadId = 'thread-1';

        httpClientSpy.post.mockReturnValue(of(mockResponse));

        service.sendMessage(message, threadId).subscribe(response => {
            expect(response).toEqual(mockResponse);
        });

        expect(httpClientSpy.post).toHaveBeenCalledWith(
            expect.stringContaining('/api/chat'),
            expect.objectContaining({ message, thread_id: threadId }),
            expect.anything()
        );
    });

    it('should get threads', () => {
        const mockThreads: Thread[] = [
            { thread_id: '1', user_id: 'test-user', title: 'Thread 1' },
            { thread_id: '2', user_id: 'test-user', title: 'Thread 2' }
        ];

        httpClientSpy.get.mockReturnValue(of({ threads: mockThreads }));

        service.getThreads().subscribe(response => {
            expect(response.threads).toEqual(mockThreads);
        });

        expect(httpClientSpy.get).toHaveBeenCalledWith(
            expect.stringContaining('/api/threads'),
            expect.anything()
        );
    });

    it('should get history', () => {
        const mockHistory: HistoryResponse = {
            messages: [
                { type: 'human', content: 'Hi' },
                { type: 'ai', content: 'Hello' }
            ]
        };
        const threadId = 'thread-1';

        httpClientSpy.get.mockReturnValue(of(mockHistory));

        service.getHistory(threadId).subscribe(response => {
            expect(response).toEqual(mockHistory);
        });

        expect(httpClientSpy.get).toHaveBeenCalledWith(
            expect.stringContaining(`/api/threads/${threadId}/history`),
            expect.anything()
        );
    });

    it('should delete thread', () => {
        const threadId = '1';
        httpClientSpy.delete.mockReturnValue(of({ status: 'deleted' }));

        service.deleteThread(threadId).subscribe(res => {
            expect(res).toEqual({ status: 'deleted' });
        });

        expect(httpClientSpy.delete).toHaveBeenCalledWith(
            expect.stringContaining(`/api/threads/${threadId}`),
            expect.anything()
        );
    });
});
