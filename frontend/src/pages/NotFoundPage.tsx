import { Compass, Home } from "lucide-react";
import { Link } from "react-router-dom";
import { EmptyState } from "@/components/common/States";
import { Button } from "@/components/ui/button";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";

export function NotFoundPage({ what = "page" }: { what?: string }) {
  useDocumentTitle("Not found");
  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <EmptyState
        icon={Compass}
        title={`This ${what} could not be found`}
        description="It may have been deleted, or the link is wrong."
        action={
          <Button asChild>
            <Link to="/">
              <Home /> Back to dashboard
            </Link>
          </Button>
        }
        className="w-full max-w-lg border-solid bg-card"
      />
    </div>
  );
}
