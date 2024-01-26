create or replace function get_user_poppularity_score(target_user_id int)
    returns numeric
    language plpgsql
    -- This function returns -1 as indication of null for inappropriate results need to be avoided in front of client
    as
    $$

    declare 
        poppularity_multiplier numeric;
        score numeric;

    begin

        -- Computing Poppularity Multiplier

        select count(g.analyticprofile_id) into poppularity_multiplier from auth2_analyticprofile_profile_views g group by g.analyticprofile_id having g.analyticprofile_id= (select id from auth2_analyticprofile where profile_id=target_user_id);

        select (poppularity_multiplier/(impressions+1)) into poppularity_multiplier from auth2_analyticprofile where profile_id=target_user_id;

        -- Computing Score

        select ln(count(g.from_profile_id)) into score from auth2_profile_reachers g group by g.from_profile_id having g.from_profile_id=target_user_id; 

        select (score + log(2.0, count(g.from_profile_id))) into score from auth2_profile_marks g group by g.to_profile_id having g.to_profile_id= target_user_id;

        if poppularity_multiplier is null or score is null then return 0; end if;

        return poppularity_multiplier*score;

    end;

$$;

create or replace function get_u2u_local_score(target_user_id int, iter_user_id int)
    returns numeric
    language plpgsql
    -- This function returns -1 as indication of null for inappropriate results need to be avoided in front of client
    as
    $$

    declare 
        already_reached boolean := false;
        score numeric := get_user_poppularity_score(iter_user_id);
        target_user_ip text;
        iter_user_ip text;
        ip_difference numeric;

    begin
        -- Initially we need to check if both id is same there is no ParentMoto fulfilled/dont wanna display himself
        if target_user_id = iter_user_id then
            return -1; -- Add to array if score is not -1
        end if;
        -- Check if user already know him/reached him
        select true into already_reached from auth2_profile_reachers where from_profile_id=iter_user_id and to_profile_id=target_user_id;

        if already_reached is true then

            return 0; -- Its ok to recommend but no point of it!
        end if;

        -- In computation, we multiply score[0-1] with their nearness_score[0-10] and return result
        -- If possible in future, we can also consier parameter of updated_at
        -- ip4*(255*4)+ip3(255*3)+ip2(255*2)+ip1(255*1) is unique per sets of diferent IPs
            -- Other approach is to write 4 nested sub-queries (Computationally expensieve)
        -- sort by ip_difference_score

        select ip::text into target_user_ip from auth2_profilepoint where profile_id=target_user_id;

        select ip::text into iter_user_ip from auth2_profilepoint where profile_id=iter_user_id;

        -- This constant is  maximum ip_difference possible
        ip_difference = 10 - ((
            abs(SPLIT_PART(target_user_ip, '.', 1)::int - SPLIT_PART(iter_user_ip, '.', 1)::int)*(255*4)+
            abs(SPLIT_PART(target_user_ip, '.', 2)::int - SPLIT_PART(iter_user_ip, '.', 2)::int)*(255*3)+
            abs(SPLIT_PART(target_user_ip, '.', 3)::int - SPLIT_PART(iter_user_ip, '.', 3)::int)*(255*2)+
            abs(SPLIT_PART(SPLIT_PART(target_user_ip, '.', 4), '/', 1)::int - SPLIT_PART(SPLIT_PART(iter_user_ip, '.', 4), '/', 1)::int)*(255*1))::numeric/25080640)*10; 

        select score*ip_difference into score;

        return score;

    end;

$$;

create or replace function get_u2u_global_score(target_user_id int, iter_user_id int)
    returns numeric
    language plpgsql
    -- This function returns -1 as indication of null for inappropriate results need to be avoided in front of client
    as
    $$

    declare 
        already_reached boolean := false;
        score numeric := get_user_poppularity_score(iter_user_id);
        reaches_common_ratio numeric;
        bookmarks_common_ratio numeric;
        -- In future we can optimize this further based on profileClicks also :D

    begin
        -- Initially we need to check if both id is same there is no ParentMoto fulfilled/dont wanna display himself
        if target_user_id = iter_user_id then
            return -1; -- Add to array if score is not -1
        end if;

        -- Check if user already know him/reached him
        select true into already_reached from auth2_profile_reachers where from_profile_id=iter_user_id and to_profile_id=target_user_id;

        if already_reached = true then
            return 0; -- Its ok to recommend but no point of it!
        end if;
        --Count Actionable numerator (Reaches)
        select count(from_profile_id)*10 into reaches_common_ratio from (select * from auth2_profile_reachers where from_profile_id=target_user_id and to_profile_id in (select to_profile_id from auth2_profile_reachers where from_profile_id=iter_user_id)) as foo group by from_profile_id;

        if reaches_common_ratio is null then 
            reaches_common_ratio := 0;
        else 
            -- Count Total effective denominator (Reaches)
            select (reaches_common_ratio/min(count)) into reaches_common_ratio from (select count(to_profile_id) from auth2_profile_reachers group by from_profile_id having from_profile_id=target_user_id or from_profile_id=iter_user_id) t;
        end if;


        -- In YouMayKnowSection we get user_plain_score and filter according to IP address of client

        --Count Actionable numerator (Bookmarks)
        select count(from_profile_id)*10 into bookmarks_common_ratio from (select * from auth2_profile_marks where from_profile_id=target_user_id and to_profile_id in (select to_profile_id from auth2_profile_marks where from_profile_id=iter_user_id)) as foo group by from_profile_id;

        if bookmarks_common_ratio is null then
            bookmarks_common_ratio := 0;
        else
            -- Count Total effective denominator (Bookmarks)
            -- select (bookmarks_common_ratio/min(count)) into bookmarks_common_ratio from (select count(to_profile_id) from auth2_profile_marks group by from_profile_id having from_profile_id=target_user_id or from_profile_id=iter_user_id) t;
            EXECUTE 'select ($1/min(count)) from (select count(to_profile_id) from auth2_profile_marks group by from_profile_id having from_profile_id=$2 or from_profile_id=$3) t;' into bookmarks_common_ratio using ( case when bookmarks_common_ratio is null then 0 else bookmarks_common_ratio end), target_user_id, iter_user_id;
        end if;
        -- format(
        --     quote_ident(( case when bookmarks_common_ratio is null then 0 else bookmarks_common_ratio end)::text),
        --     quote_ident(target_user_id),
        --     quote_ident(iter_user_id)
        -- );

        select score * ((reaches_common_ratio + bookmarks_common_ratio) / 2) into score; 

        return score;

    end;
$$;



-- Following queries list all predictions, Now just make model as recommendation set pointer to initial after setting it

-- We'll create new recommendation series when app startup and loads for first recommendations, then after we follow below approach
-- SO two commands [CREATE_RECOMMENDATIONS, FETCH_RECOMMENDATIONS] on AppStartup(InitialLoad);;we'll detect this by checking if (requested_counter or page)==0
-- Otherwise [FETCH_RECCOMENDATIONS] NO-Circullarity-Prevention (CREATES DUPLICATIONS)
-- So that each time app restartes it has something to show instead of NOTHING!
-- BOOOM! no need for any pointer just delete predicted posts after returning to backend server
-- Make sure it'll insert as `raw` without ORM, after creation it'll return first five elements and set pointer to 5

-- For fetching `ReachOut` recommendations use [CREATE_RECOMMENDATIONS]
-- select iter.id as profile_id ,get_u2u_global_score(1,iter.id::int) as score from auth2_profile iter where iter.id != 1 order by score desc;
-- For fetching `YouMayKNow`/`NearYou` recommendations use
    -- select iter.id as profile_id ,get_u2u_local_score(1,iter.id::int) as score from auth2_profile iter where iter.id != 1 and score >= 0 order by score desc;
