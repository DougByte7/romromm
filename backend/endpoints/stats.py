from endpoints.responses.stats import StatsReturn
from handler.database import db_stats_handler
from handler.database.base_handler import sync_session
from utils.router import APIRouter

router = APIRouter(
    prefix="/stats",
    tags=["stats"],
)


@router.get("")
def stats() -> StatsReturn:
    """Endpoint to return the current RomM stats

    Returns:
        dict: Dictionary with all the stats
    """

    with sync_session.begin() as session:
        return {
            "PLATFORMS": db_stats_handler.get_platforms_count(session=session),
            "ROMS": db_stats_handler.get_roms_count(session=session),
            "SAVES": db_stats_handler.get_saves_count(session=session),
            "STATES": db_stats_handler.get_states_count(session=session),
            "SCREENSHOTS": db_stats_handler.get_screenshots_count(session=session),
            "TOTAL_FILESIZE_BYTES": db_stats_handler.get_total_filesize(session=session),
        }

