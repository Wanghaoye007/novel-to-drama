import { NextResponse } from "next/server";
import { PlatformAuthError, QuotaError } from "./platform-context";

export function platformErrorResponse(error: unknown): NextResponse | null {
  if (error instanceof PlatformAuthError) {
    return NextResponse.json(
      { error: error.message },
      { status: error.status }
    );
  }
  if (error instanceof QuotaError) {
    return NextResponse.json(
      { error: error.message, quota: error.quota },
      { status: error.status }
    );
  }
  return null;
}
