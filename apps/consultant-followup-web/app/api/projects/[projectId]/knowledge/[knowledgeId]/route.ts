import { NextResponse } from "next/server";

export async function PATCH() {
  return NextResponse.json(
    {
      error: "knowledge_management_removed",
      detail: "Knowledge card mutation endpoints are deprecated; use flashcard actions in Know More.",
    },
    { status: 410 }
  );
}

export async function DELETE() {
  return NextResponse.json(
    {
      error: "knowledge_management_removed",
      detail: "Knowledge card mutation endpoints are deprecated; use flashcard actions in Know More.",
    },
    { status: 410 }
  );
}
