"use client"

import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from "remark-gfm";

function Markdown({ children }: { children: string }) {
    return (
        <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
                a: ({ ...props }) => (
                    <a
                        {...props}
                        className="text-blue-600 dark:text-blue-400 underline underline-offset-2"
                        target={props.href?.startsWith('#') ? undefined : "_blank"}
                        rel={props.href?.startsWith('#') ? undefined : "noreferrer"}
                    />
                ),
                p: ({ ...props }) => <p {...props} className="whitespace-pre-wrap" />,
                ul: ({ ...props }) => <ul {...props} className="list-disc pl-6 space-y-1" />,
                ol: ({ ...props }) => <ol {...props} className="list-decimal pl-6 space-y-1" />,
                li: ({ ...props }) => <li {...props} />,
                code: ({ children, className, ...props }) => (
                    <code
                        {...props}
                        className={[
                            "rounded bg-gray-100 dark:bg-gray-900 px-1 py-0.5",
                            className ?? "",
                        ].join(" ")}
                    >
                        {children}
                    </code>
                ),
                pre: ({ ...props }) => (
                    <pre
                        {...props}
                        className="overflow-x-auto rounded bg-gray-100 dark:bg-gray-900 p-3"
                    />
                ),
            }}
        >
            {children}
        </ReactMarkdown>
    );
}

export default function Home() {
    const [idea, setIdea] = useState<string>('');
    const [inputText, setInputText] = useState<string>('');
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [ingestUrl, setIngestUrl] = useState<string>('');
    const [ingestFile, setIngestFile] = useState<File | null>(null);
    const [ingestMode, setIngestMode] = useState<'url' | 'file'>('url');
    const [ingestion_response, setIngestionResponse] = useState<string>('');
    const [ingestionError, setIngestionError] = useState<string>('');
    const [isIngesting, setIsIngesting] = useState<boolean>(false);
    const [fileInputKey, setFileInputKey] = useState<number>(0);

    const maxFileSizeBytes = 5 * 1024 * 1024;

    const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        if (isLoading) return;

        setIdea('');
        setIsLoading(true);

        try {
            const res = await fetch('/api', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ text: inputText }),
            });

            const text = await res.text();
            if (!res.ok) throw new Error(text || `Request failed (${res.status})`);

            setIdea(text);
        } catch (err) {
            const message = err instanceof Error ? err.message : String(err);
            setIdea('Error: ' + message);
        } finally {
            setIsLoading(false);
        }
    };

    const handleUrlIngestion = async (event?: React.FormEvent<HTMLFormElement> | React.MouseEvent<HTMLButtonElement>) => {
        event?.preventDefault();
        if (isIngesting) return;

        setIngestionResponse('');
        setIngestionError('');
        setIsIngesting(true);

        try {
            const res = await fetch('/ingest', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url: ingestUrl }),
            });

            const text = await res.text();
            if (!res.ok) throw new Error(text || `Request failed (${res.status})`);

            setIngestionResponse(text);
        } catch (err) {
            const message = err instanceof Error ? err.message : String(err);
            setIngestionResponse('Error: ' + message);
        } finally {
            setIsIngesting(false);
        }
    };

    const handleFileIngestion = async (event?: React.FormEvent<HTMLFormElement> | React.MouseEvent<HTMLButtonElement>) => {
        event?.preventDefault();
        if (isIngesting) return;

        if (!ingestFile) {
            setIngestionError('Please select a file to ingest.');
            return;
        }

        if (ingestFile.size > maxFileSizeBytes) {
            setIngestionError('File size cannot exceed 5 MB.');
            return;
        }

        setIngestionResponse('');
        setIngestionError('');
        setIsIngesting(true);

        try {
            const formData = new FormData();
            formData.append('file', ingestFile);

            const res = await fetch('/ingest-file', {
                method: 'POST',
                body: formData,
            });

            const text = await res.text();
            if (!res.ok) throw new Error(text || `Request failed (${res.status})`);

            setIngestionResponse(text);
        } catch (err) {
            const message = err instanceof Error ? err.message : String(err);
            setIngestionResponse('Error: ' + message);
        } finally {
            setIsIngesting(false);
        }
    };

    const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0] ?? null;
        setIngestionError('');

        if (!file) {
            setIngestFile(null);
            return;
        }

        if (file.size > maxFileSizeBytes) {
            setIngestionError('File size cannot exceed 5 MB.');
            setIngestFile(null);
            setFileInputKey((prev) => prev + 1);
            return;
        }

        setIngestFile(file);
    };

    const handleIngestionSubmit = (event: React.FormEvent<HTMLFormElement>) => {
        if (ingestMode === 'url') {
            void handleUrlIngestion(event);
            return;
        }

        void handleFileIngestion(event);
    };

    const handleIngestButtonClick = (
        mode: 'url' | 'file',
        handler: (event?: React.MouseEvent<HTMLButtonElement>) => Promise<void>
    ) => async (event: React.MouseEvent<HTMLButtonElement>) => {
        if (ingestMode !== mode) {
            setIngestMode(mode);
            return;
        }

        await handler(event);
    };

    return (
        <main className="p-8 font-sans">
            <h1 className="text-3xl font-bold mb-4">
                Personal RAG Agent
            </h1>
            <form
                onSubmit={handleSubmit}
                className="w-full max-w-2xl p-6 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm space-y-4"
                aria-busy={isLoading}
            >
                <input
                    type="text"
                    value={inputText}
                    onChange={(event) => setInputText(event.target.value)}
                    placeholder="Describe your idea..."
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-transparent text-gray-900 dark:text-gray-100"
                />
                <button
                    type="submit"
                    disabled={isLoading}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-60 disabled:cursor-not-allowed"
                >
                    {isLoading && (
                        <span
                            className="h-4 w-4 rounded-full border-2 border-white/40 border-t-white animate-spin"
                            aria-hidden="true"
                        />
                    )}
                    {isLoading ? 'Generating…' : 'Generate'}
                </button>
                {idea && (
                    <div className="text-gray-900 dark:text-gray-100">
                        <Markdown>{idea}</Markdown>
                    </div>
                )}
            </form>

            <form
                onSubmit={handleIngestionSubmit}
                className="mt-6 w-full max-w-2xl p-6 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm space-y-4"
                aria-busy={isIngesting}
            >
                {ingestMode === 'url' ? (
                    <input
                        type="url"
                        value={ingestUrl}
                        onChange={(event) => setIngestUrl(event.target.value)}
                        placeholder="Enter website url to ingest"
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-transparent text-gray-900 dark:text-gray-100"
                    />
                ) : (
                    <input
                        key={fileInputKey}
                        type="file"
                        onChange={handleFileChange}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-transparent text-gray-900 dark:text-gray-100"
                    />
                )}
                <div className="flex flex-wrap items-center gap-3">
                    <button
                        type="button"
                        disabled={isIngesting}
                        onClick={handleIngestButtonClick('url', handleUrlIngestion)}
                        className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-green-600 text-white hover:bg-green-700 disabled:opacity-60 disabled:cursor-not-allowed"
                    >
                        {isIngesting && ingestMode === 'url' && (
                            <span
                                className="h-4 w-4 rounded-full border-2 border-white/40 border-t-white animate-spin"
                                aria-hidden="true"
                            />
                        )}
                        {isIngesting && ingestMode === 'url' ? 'Ingesting data...' : 'Ingest url'}
                    </button>
                    <button
                        type="button"
                        disabled={isIngesting}
                        onClick={handleIngestButtonClick('file', handleFileIngestion)}
                        className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-60 disabled:cursor-not-allowed"
                    >
                        {isIngesting && ingestMode === 'file' && (
                            <span
                                className="h-4 w-4 rounded-full border-2 border-white/40 border-t-white animate-spin"
                                aria-hidden="true"
                            />
                        )}
                        {isIngesting && ingestMode === 'file' ? 'Ingesting data...' : 'Ingest File'}
                    </button>
                </div>
                {ingestionError && (
                    <div className="text-sm text-red-600 dark:text-red-400">
                        {ingestionError}
                    </div>
                )}
                {ingestion_response && (
                    <div className="text-gray-900 dark:text-gray-100">
                        <Markdown>{ingestion_response}</Markdown>
                    </div>
                )}
            </form>
        </main>
    );
}
