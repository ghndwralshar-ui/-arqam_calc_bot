from datetime import datetime, timedelta
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def init_db():
    print("🟢 قاعدة البيانات السحابية (Supabase) متصلة وجاهزة بنجاح!")

def db_get_user(user_id):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        res = supabase.table("users").select("*").eq("user_id", user_id).execute()
        rows = res.data if hasattr(res, 'data') else []
        if not rows:
            all_res = supabase.table("users").select("user_sequence").execute()
            all_u = all_res.data if hasattr(all_res, 'data') else []
            max_seq = max([r.get("user_sequence", 0) for r in all_u]) if all_u else 0
            new_seq = max_seq + 1

            new_data = {
                "user_id": user_id,
                "balance": 0.0,
                "referrals": 0,
                "referred_by": 0,
                "joined_date": now_str,
                "is_banned": 0,
                "user_sequence": new_seq,
                "reward_claimed": 0
            }
            supabase.table("users").insert(new_data).execute()
            return {
                "balance": 0.0, "referrals": 0, "referred_by": 0, "is_banned": 0, "user_sequence": new_seq, "reward_claimed": 0
            }
        
        row = rows[0]
        return {
            "balance": float(row.get("balance", 0.0)),
            "referrals": int(row.get("referrals", 0)),
            "referred_by": int(row.get("referred_by", 0)),
            "is_banned": int(row.get("is_banned", 0)),
            "user_sequence": int(row.get("user_sequence", 1)),
            "reward_claimed": int(row.get("reward_claimed", 0))
        }
    except Exception as e:
        print(f"db_get_user Error: {e}")
        return {"balance": 0.0, "referrals": 0, "referred_by": 0, "is_banned": 0, "user_sequence": 1, "reward_claimed": 0}

def db_update_balance(user_id, amount, mode="add"):
    u = db_get_user(user_id)
    current_bal = float(u.get("balance", 0.0))
    if mode == "add":
        new_bal = current_bal + float(amount)
    elif mode == "deduct":
        new_bal = max(0.0, current_bal - float(amount))
    else:
        new_bal = current_bal

    try:
        supabase.table("users").update({"balance": new_bal}).eq("user_id", user_id).execute()
    except Exception as e:
        print(f"db_update_balance Error: {e}")

def db_get_advanced_stats():
    try:
        res = supabase.table("users").select("*").execute()
        users = res.data if hasattr(res, 'data') else []
        total_users = len(users)
        total_balances = sum(float(u.get("balance", 0.0)) for u in users)
        total_referrals = sum(int(u.get("referrals", 0)) for u in users)

        now = datetime.now()
        yesterday = now - timedelta(days=1)
        new_24h = 0
        for u in users:
            joined_str = u.get("joined_date", "")
            if joined_str:
                try:
                    j_date = datetime.strptime(joined_str.strip(), "%Y-%m-%d %H:%M:%S")
                    if j_date >= yesterday: new_24h += 1
                except Exception:
                    try:
                        j_date = datetime.strptime(joined_str.strip()[:10], "%Y-%m-%d")
                        if j_date >= yesterday.replace(hour=0, minute=0, second=0, microsecond=0): new_24h += 1
                    except Exception:
                        pass

        sorted_users = sorted(users, key=lambda x: int(x.get("referrals", 0)), reverse=True)
        top_refs = [(u["user_id"], int(u.get("referrals", 0))) for u in sorted_users[:5] if int(u.get("referrals", 0)) > 0]

        return {"total_users": total_users, "total_balances": total_balances, "total_referrals": total_referrals, "new_24h": new_24h, "top_refs": top_refs}
    except Exception as e:
        print(f"db_get_advanced_stats Error: {e}")
        return {"total_users": 0, "total_balances": 0, "total_referrals": 0, "new_24h": 0, "top_refs": []}

def db_get_all_users():
    try:
        res = supabase.table("users").select("user_id").eq("is_banned", 0).execute()
        rows = res.data if hasattr(res, 'data') else []
        return [row["user_id"] for row in rows] if rows else []
    except Exception:
        return []

def is_admin_or_sub(user_id, admin_id):
    if user_id == admin_id:
        return True
    try:
        res = supabase.table("sub_admins").select("admin_id").eq("admin_id", user_id).execute()
        rows = res.data if hasattr(res, 'data') else []
        return len(rows) > 0
    except Exception:
        return False

def get_all_sub_admins():
    try:
        res = supabase.table("sub_admins").select("admin_id").execute()
        rows = res.data if hasattr(res, 'data') else []
        return [row["admin_id"] for row in rows] if rows else []
    except Exception:
        return []
