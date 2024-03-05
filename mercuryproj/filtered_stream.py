import requests
import os
import json

# To set your enviornment variables in your terminal run the following line:
# export 'BEARER_TOKEN'='<your_bearer_token>'
bearer_token = os.environ.get("BEARER_TOKEN")

tweet_params = {
    "tweet.fields": "id,text,edit_history_tweet_ids,attachments,author_id,conversation_id,created_at,entities,in_reply_to_user_id,lang,public_metrics,referenced_tweets,reply_settings",
    "user.fields": "id,name,username,created_at,description,entities,location,pinned_tweet_id,profile_image_url,protected,public_metrics,url,verified",
    "media.fields": "media_key,type,url,duration_ms,height,preview_image_url,public_metrics,width",
    "expansions": "author_id,referenced_tweets.id,attachments.media_keys",
}

ff = open('filtered_stream_output2.txt', 'a')


def bearer_oauth(r):
    """
    Method required by bearer token authentication.
    """

    r.headers["Authorization"] = f"Bearer {bearer_token}"
    r.headers["User-Agent"] = "v2FilteredStreamPython"
    return r


def get_rules():
    response = requests.get(
        "https://api.twitter.com/2/tweets/search/stream/rules", auth=bearer_oauth
    )
    if response.status_code != 200:
        raise Exception(
            "Cannot get rules (HTTP {}): {}".format(response.status_code, response.text)
        )
    print(json.dumps(response.json()))
    return response.json()


def delete_all_rules(rules):
    if rules is None or "data" not in rules:
        return None

    ids = list(map(lambda rule: rule["id"], rules["data"]))
    payload = {"delete": {"ids": ids}}
    response = requests.post(
        "https://api.twitter.com/2/tweets/search/stream/rules",
        auth=bearer_oauth,
        json=payload
    )
    if response.status_code != 200:
        raise Exception(
            "Cannot delete rules (HTTP {}): {}".format(
                response.status_code, response.text
            )
        )
    print(json.dumps(response.json()))


def set_rules(delete):
    # You can adjust the rules if needed
    sample_rules = [
        {
            "value": 'sample:10 (from:TrialsiteN OR from:CaliforniaGlobe OR from:ActualidadRT OR from:FL_Daily OR from:homenaturalcure OR from:Electroversenet OR from:IA_Journal_ OR from:TheOhioStar OR from:ConsPolToday OR from:TheMichiganStar OR from:TheMinnesotaSun OR from:MehrnewsCom OR from:QNationUS OR from:RonPaulInstitut OR from:ChinaDailyUSA OR from:OopstopC OR from:AliciaFixLuke OR from:catholic_proud OR from:russiabeyond OR from:Evie_Magazine OR from:CitizensJourn OR from:VozWire OR from:stopvaccinating OR from:infolibnews OR from:vadogwoodnews OR from:CGTNOfficial OR from:FocusFamily OR from:DisrnNews OR from:InvestWatchBlog OR from:Intl_Highlife OR from:AlachuaChronic1 OR from:thegailygrind OR from:tampafreepress OR from:UncoverDC OR from:DrChrisNorthrup OR from:CopperCourier OR from:standforhealth1 OR from:JDRucker OR from:TTAVOfficial OR from:WSWS_Updates OR from:MiMighty OR from:TheFirstonTV OR from:PoliTribune OR from:MagaVoter OR from:TheTentacle1 OR from:LancasterCouri1 OR from:Trend_Politics)',
            "tag": "0"},
        {
            "value": 'sample:10 (from:UpNorthNewsWI OR from:americanoreport OR from:Virginia_Works OR from:TheKeystone OR from:GanderNewsroom OR from:CardinalAndPine OR from:thelibertyloft OR from:jonrappoport OR from:thelatribune OR from:CRBeyond OR from:mercola OR from:freedomfirstnet OR from:PanData19 OR from:HIT_Evidence OR from:RespectNH OR from:CovidAnalysis OR from:DrCraigRoberts OR from:AriseOhio OR from:kellybroganmd OR from:davidjsorensen OR from:thehealthguy OR from:patriotproj OR from:TheVAStar OR from:TruNews OR from:Rational_Ground OR from:MayadeenEnglish OR from:herbhealthhappy OR from:standup_fl OR from:SteveRotter OR from:ColoradoHerald OR from:MillionsAgainst OR from:GeorgiaStarNews OR from:PressPopulist OR from:NewsSurvive OR from:UW_Inter OR from:ThePatsGazette OR from:NewsBecker OR from:OneGreenPlanet OR from:RealRawNews1 OR from:Russia_Main OR from:IdahoTribune OR from:flcapitalstar OR from:ConservRoof OR from:usawirenews OR from:COVID19Up1 OR from:RagingAmericans OR from:brownstoneinst)',
            "tag": "1"},
        {
            "value": 'sample:10 (from:TruthForHealth OR from:TheStarNewsNet OR from:100PercFEDUP OR from:NevadaGlobe OR from:WIDailyStar OR from:TheRealFrankSp1 OR from:rightwingalert OR from:WatchSalemNews OR from:AZFreeNews OR from:PADailyStar OR from:vtforeignpolicy OR from:american_mirror OR from:rushlimbaugh OR from:NaturalSolution OR from:MDiplomacyWORLD OR from:NewsLiveFree OR from:Leafly OR from:interfax_news OR from:jubals OR from:ValiantNewsLive OR from:YikesToday OR from:REALfarmacy OR from:ConnecticutStar OR from:PalmerReport OR from:Plandemic3Movie OR from:medicaldaily OR from:LeadingReport OR from:Greg_Palast OR from:ActivistPost OR from:Antiwarcom OR from:toddstarnes OR from:DrEddyClinic OR from:Whatfinger1 OR from:RadioPatriot OR from:respect_stories OR from:GA_Record OR from:Unshackled_QE OR from:GeoengineeringW OR from:demcommies OR from:FrontlineNewsUS OR from:NeonNettle OR from:ChiDefender OR from:greenmedinfo OR from:ReviewOrie45124 OR from:creatdestmed OR from:wikileaks OR from:realJoeHoft)',
            "tag": "2"},
        {
            "value": 'sample:10 (from:SCJournalOnline OR from:TheDuranReal OR from:dgaytandzhieva OR from:GeopolitikaEN OR from:VigilantNews OR from:Tasnimnews_EN OR from:Stewpeters1132 OR from:glennbeck OR from:PeggyHall OR from:KevinJacksonTBS OR from:ANTHONYBLOGAN OR from:aciprensa OR from:HeartlandInst OR from:LiveAction OR from:BlackNews OR from:thedailybanter OR from:unhealthytruth OR from:barenakedislam OR from:GraniteGrok OR from:TnA1776 OR from:intellectualTO OR from:joeimbriano777 OR from:WetpaintTV OR from:horowitz39 OR from:Worldtruthtvs OR from:christianhlines OR from:AmActionNews OR from:tassagency_en OR from:TechTimes_News OR from:TheHayride OR from:MadWorldNews OR from:natureheals OR from:OrganicConsumer OR from:jihadwatchRS OR from:MediterraneoDGT OR from:elamerican OR from:lifebiomedguru OR from:ACLJ OR from:dailykos OR from:lewrockwell OR from:SOTTnet OR from:JimBakkerShow OR from:TheRightScoop OR from:GreggJarrett OR from:drdavidfriedman OR from:DowntrendCom OR from:nrlc OR from:ConnersClinic)',
            "tag": "3"},
        {
            "value": 'sample:10 (from:aawsat_eng OR from:FreedomsPhoenix OR from:DonaldCourter OR from:NewsWndr OR from:DesertReview OR from:MoonofA OR from:CR OR from:bitcoinist OR from:DrMichaelMurray OR from:HealthyNews2day OR from:Crypto_Potato OR from:COpeakpolitics OR from:IranFrontPage OR from:Baltimore_Times OR from:GreatGameIndia OR from:FunkerActual OR from:AFF_PATRIOT OR from:DCEngager OR from:AltHealthWORKS OR from:AmerIndependent OR from:WhiteCoatWaste OR from:Slay_News_ OR from:SaraCarterDC OR from:PatriotPost OR from:FinishTheRace OR from:KUSINews OR from:ukraina_ru OR from:powerlineUS OR from:VisionTimesLife OR from:VisionTWorld OR from:BlacklistedNews OR from:ichudov OR from:indiesentinel OR from:hrtwarming OR from:RussiaInsider OR from:VineyardSaker OR from:peoplesvoice_tv OR from:MSNBC OR from:AnonymousNewsHQ OR from:UnleashMind OR from:Russia_Truth OR from:shitexpress OR from:EpochTimes OR from:goop OR from:IAStartingLine OR from:JesusDaily OR from:YourNewsMedia OR from:Streamdotorg OR from:LifeZette)',
            "tag": "4"},
        {
            "value": 'sample:10 (from:PDChina OR from:TheNatPulse OR from:trtworld OR from:aSciEnthusiast OR from:ConservPost OR from:R_republic_411 OR from:theBerniePost OR from:Prntly OR from:BuckSexton OR from:AgeofAutism OR from:usnewson OR from:AmericanThinker OR from:rianru OR from:PravdaRu OR from:SputnikInt OR from:WTFfacts OR from:co_firing_line OR from:thinkamericana OR from:NatEnquirer OR from:TimesVision OR from:thegoodgodabove OR from:charisma_news OR from:drjoshaxe OR from:CFACT OR from:ReadTheHornNews OR from:eatLocalGrown OR from:MediaTakeoutTV OR from:realDailyWire OR from:newsbreakApp OR from:MintPressNews OR from:WorldTribune OR from:DailyClout OR from:BCNbcn OR from:AAPSonline OR from:amer_pregnancy OR from:NewsRescue OR from:worldnetdaily OR from:TheAltDaily OR from:joinvaxxter OR from:BreitbartNews OR from:OnlinePatriots OR from:TwitchyTeam OR from:V_of_Europe OR from:WakingTimes OR from:GrabienMedia OR from:XHNews OR from:AJEnglish OR from:cdalerts OR from:Strange_Sounds OR from:WestonAPrice)',
            "tag": "5"},
        {
            "value": 'sample:10 (from:EasternHerald OR from:realMaryFanning OR from:justworldtweets OR from:drsircus OR from:FPPTim OR from:CCTV OR from:Saudi_Gazette OR from:ClashDailyCom OR from:srbininfo OR from:wellbeingjourna OR from:Church_Militant OR from:Consortiumnews OR from:arabnews OR from:awarenessactcom OR from:Cubanoselmundo OR from:MustReadAlaska OR from:beforeitsnews OR from:chicago_wire OR from:theamgreatness OR from:WEEKLYBLITZ OR from:NewsFromCCT OR from:SvidokInfo OR from:djockers5 OR from:_HealingOracle_ OR from:SANAEnOfficial OR from:TheGoldWaterUS OR from:TehranTimes79 OR from:livelovefruit OR from:210observer OR from:tagDivOfficial OR from:TheNorthStar OR from:picphysicians OR from:drsimonegold OR from:allnewspipeline OR from:NVICLoeDown OR from:GreenWWarriors OR from:IrnaEnglish OR from:UpliftingToday OR from:TheTNStar OR from:209TimesCA OR from:AmericaDefiant OR from:Guardemocracy OR from:RedBlueDivide OR from:USTruthWire OR from:LosAngelesBlade OR from:DemocracyDocket OR from:remnantnews)',
            "tag": "6"},
        {
            "value": 'sample:10 (from:CzebotarJessie OR from:TiwannaRN42 OR from:RealBruceClark OR from:LivePDDave1 OR from:FcSunnee OR from:VanEmmerickKris OR from:enfree1993 OR from:RealScottRitter OR from:SaltyCracker9 OR from:saisaisaiiz OR from:DrewHLive OR from:RekietaLaw OR from:DarrenJBeattie OR from:WayV_official OR from:heiankyo_327 OR from:catturd2 OR from:Dadidice1 OR from:ShenYue_TH OR from:Baklava_USA OR from:annvandersteel OR from:ReadeAlexandra OR from:ericmetaxas OR from:NTDNews OR from:griptmedia OR from:MakisMD OR from:1776DrRick OR from:LWCnewswire OR from:PaulMitchell_AB OR from:TEN__IDN OR from:teriksson9 OR from:theblaze OR from:WayV_China_STA OR from:Pancho66196600 OR from:KeillerDon OR from:JasonMillerinDC OR from:KanekoaTheGreat OR from:JohnJGaltrules OR from:queenb_wiov OR from:ModiGovt2 OR from:themarketear OR from:fmeeus1 OR from:laralogan OR from:WallStreetApes OR from:mollie_don OR from:tmtm1253_ OR from:TrumpWarRoom OR from:Article3Project OR from:narshmallow813 OR from:GOP OR from:Jakelyneloiola_)',
            "tag": "7"},
        {
            "value": 'sample:10 (from:PoliceThePolic1 OR from:EMichaelJones1 OR from:babulal_vasant OR from:swati_gs OR from:JimFergusonUK OR from:DaveAtherton20 OR from:JudiciaryGOP OR from:FranceRsistanc1 OR from:blessingfowoba OR from:2Moori OR from:weichuanyufu OR from:konnect_danielk OR from:theprofsrecord OR from:MdBreathe OR from:Beyond_Mystic OR from:AaronOtsuka OR from:nataliegwinters OR from:Finanzas_Times OR from:Michael_J_Matt OR from:Deejo53513317 OR from:sohbunshu OR from:NationalFile OR from:jacksonhinklle OR from:HowleyReporter OR from:MammothNationUS OR from:Joe7993 OR from:courage04ever OR from:nama_wz OR from:Babygravy9 OR from:chen88888899 OR from:pepesgrandma OR from:mikepompeo OR from:YaochensClub_TH OR from:Apex_WW OR from:NineOfficial_TH OR from:EntTofu OR from:ALEGRA1988 OR from:Doctor_I_am_The OR from:lovely__dollS2 OR from:kacdnp91 OR from:xrenaur OR from:Zoogerdee2024 OR from:ConservativeAd5 OR from:WZCOrangeGarden OR from:SheriffClarke OR from:TonyClimate OR from:BonginoReport OR from:daywithshua)',
            "tag": "8"},
        {
            "value": 'sample:10 (from:maapaadubu OR from:laurenboebert OR from:headBONDmeLWJ OR from:OANN OR from:patgill69033215 OR from:EZ2p8 OR from:GlockfordFiles OR from:jackson66368924 OR from:TheLeoTerrell OR from:stella_immanuel OR from:JustTheNews OR from:revistaoeste OR from:ShellbackProud OR from:YakToraNW OR from:BakarecPolitika OR from:JosephWulfsohn OR from:PatFish62304572 OR from:qikong_ OR from:jenmong23 OR from:MeganJia8 OR from:MartinMeinung OR from:RealPNavarro OR from:PBeatap OR from:ChanceGardi OR from:SikhForTruth OR from:WayVLand_TH OR from:RaheemKassam OR from:DrJudyAMikovits OR from:AuronMacintyre OR from:caogenxiaogex OR from:YiboW_MTJJ_KR OR from:CarolineLessar8 OR from:Covid19Critical OR from:Iowa_1776 OR from:SheldonRothMD1 OR from:lxnthaifans OR from:chiproytx OR from:theraginpatriot OR from:gho14913630 OR from:NaturallyFTW OR from:SeanTho98192182 OR from:Eloise93833941 OR from:BounPrem_TH_OFC OR from:TheEXECUTlONER_ OR from:jenocutest OR from:rickoshimizu OR from:Dover63A OR from:nickveniamin)',
            "tag": "9"},
        {
            "value": 'sample:10 (from:pcisbs1 OR from:DreaHumphrey OR from:CannConActual OR from:yongsununiverse OR from:Allenma15086871 OR from:VSainement OR from:YingJie22739040 OR from:65320Bob OR from:BobMalandrin OR from:TexasFBA4Ever OR from:tolgaozcelkk90 OR from:NXXGallery OR from:mikerreports OR from:SaiKate108 OR from:realstewpeters OR from:ConradsonJordan OR from:RealKyleMorris OR from:LeFACTEUR10 OR from:simonateba OR from:Scottnotonemor1 OR from:ClimateThere OR from:threerights1 OR from:LarsBern2 OR from:yiidream OR from:doiekunkun OR from:SF9__Unofficial OR from:GatestoneInst OR from:Whyohyme1 OR from:DrLiMengYAN1 OR from:DoctorTurtleboy OR from:WarClandestine OR from:BonsensOrg OR from:45Angelheart OR from:drgerryF OR from:lunaestreIIad0s OR from:RenzTom OR from:S1lzF6u0WSo0BzD OR from:YIZHANForeverTH OR from:its_the_Dr OR from:MachadoDarlon OR from:WuYuHengTH OR from:KDanigall OR from:Johanne31785773 OR from:Q_May_007 OR from:JontTrubek OR from:NicolasPichot6 OR from:MatthewWielicki OR from:DanaMetcalfe5)',
            "tag": "10"},
        {
            "value": 'sample:10 (from:PecanC8 OR from:woainewofficial OR from:JCondamine OR from:leslibless OR from:LD_Sceptics OR from:GeorgeFareed2 OR from:peace86774949 OR from:TEENSINTIMESTH OR from:ZHICHENGO2O5 OR from:RealGeorgeWebb1 OR from:Moms4Liberty OR from:neverlandintl OR from:IndyBeginsAt220 OR from:JovanHPulitzer OR from:goldrussh92 OR from:khaleesi77777 OR from:Baoliaogeming64 OR from:men_odins OR from:iyathoeungg OR from:SawyersGhost OR from:patrick_THFC OR from:doc_singing OR from:AJuijn OR from:No3Mos OR from:RepMTG OR from:nomandatesco OR from:Frisky60AZ OR from:LDN327 OR from:gc22gc OR from:Mayflower_21 OR from:DrShayPhD OR from:bjyxEShouse OR from:LinmoThailand OR from:HimalayaMayflo1 OR from:Synchro2021 OR from:RedPill78 OR from:blckbxnews OR from:ITSFOR813 OR from:nanavet3 OR from:Concern70732755 OR from:GuntherEagleman OR from:Fleur50559050 OR from:JamesTate121 OR from:HeyLey98657471 OR from:MaldonDonmal OR from:laura_7771 OR from:SmilingOutrage OR from:DissocialSpace OR from:LBasemi OR from:yejibyeol)',
            "tag": "11"},
        {
            "value": 'sample:10 (from:genspect OR from:WallStreetSilv OR from:SANTADANCE_TH OR from:FoxNews OR from:boyuanarchive OR from:RIKIMARU_TH OR from:alwayspptt OR from:carouru2 OR from:JhWesten OR from:LiuZhangTH OR from:UnsilencedOrg OR from:Mika_THOfficial OR from:ClaireBalan OR from:mark89894 OR from:1984IsNow1776 OR from:K2_1230_ OR from:XRPLion1 OR from:TLAVagabond OR from:beauty_gene_ OR from:oskepat_TH OR from:ShenYunCreation OR from:AntonioTweets2 OR from:happyhbd__ OR from:BanounHelene OR from:PapiTrumpo OR from:PatrickCNFC OR from:svtcontents OR from:DavidMusiker OR from:Patrick_pppatJP OR from:V_its_me_ OR from:thesoulmate95pj OR from:Real_AnTheFacts OR from:Fynnderella1 OR from:john_bumblebee OR from:ZNN_Intl OR from:justice_trail OR from:tommyboy0690 OR from:DiedSuddenlyFR OR from:BehizyTweets OR from:RDog861 OR from:tatiann69922625 OR from:FDRLST OR from:pppynklemonade OR from:Dan19726 OR from:grahamHmoore OR from:RealGregBoulden OR from:puppyydreamm OR from:ThaiLeiMiWulei OR from:JohnLeePettim13)',
            "tag": "12"},
        {
            "value": 'sample:10 (from:ForLiuYu_TH OR from:fuctmind OR from:aparanjape OR from:forchengxiao_th OR from:betterworld_24 OR from:_2019_nCoV OR from:Spiro_Ghost OR from:AdeDetective OR from:JanetTX_Blessed OR from:jamong1323 OR from:JackieC49305942 OR from:Fuknutz OR from:CreasonJana OR from:KimIversenShow OR from:MasterRaffster OR from:gongxi8cai888 OR from:anise0316 OR from:JDunlap1974 OR from:Mos_Translators OR from:KTZZXZGG OR from:jhmdrei OR from:MoBummer1 OR from:TheCounterSgnl OR from:AbeWarRoom OR from:shdegaray73 OR from:browneyegirl400 OR from:PrPatriotUS OR from:RealPepeEscobar OR from:MaryMor08180163 OR from:DeanSmi47962704 OR from:tobimono2 OR from:IamBrookJackson OR from:patreasure_ OR from:cafelockedout OR from:BrentHane OR from:DevotetoPaipai OR from:NowTheEndBegins OR from:Thomas_Binder OR from:TheRealSteve613 OR from:DrLoupis OR from:akafacehots OR from:ClownWorld_ OR from:CzeKuku2 OR from:Kc_Casey1 OR from:SamiAntinniemi OR from:NavyVeteranPaul OR from:Tony73_censored OR from:AGHuff)',
            "tag": "13"},
        {
            "value": 'sample:10 (from:EricArchambaul7 OR from:VacSafety OR from:gardenianights OR from:Bigbird32392741 OR from:stinchfield1776 OR from:Storiesofinjury OR from:PeatwasuOfc OR from:matjendav4 OR from:realTangBoYuan_ OR from:NickNkvd OR from:mkolken OR from:freenbeckynews OR from:danghwang1122 OR from:PaPaPa80755851 OR from:322_45won OR from:P_McCulloughMD OR from:andrewbostom OR from:WashTimes OR from:angie_anson OR from:JJMAMI88 OR from:dchomecoming OR from:blueskybaiyun2 OR from:DavidAsmanfox OR from:Fortfts_Trend OR from:Keltic_Witch OR from:sophiadahl1 OR from:45LVNancy OR from:Bob20227 OR from:Scott4MAGA OR from:healthbyjames OR from:SerkanK16508934 OR from:NanLee1124 OR from:CHERRYYT1026 OR from:awakenindiamov OR from:NineteamsUpdate OR from:YEJI_CNFU OR from:Robertonuzzoam OR from:RealWsiegrist OR from:Denman13897929 OR from:slk55again OR from:CartlandDavid OR from:TastyMorsel6 OR from:USAPat4DJT OR from:FBZZ19 OR from:FortftsOfficial OR from:allaboutzhaolei OR from:cassisnouveau OR from:LTRNForever)',
            "tag": "14"},
        {
            "value": 'sample:10 (from:Skeptical_Mike OR from:FringeViews OR from:guozhanshi OR from:Mesigal7 OR from:LastHawk33 OR from:RickyDoggin OR from:Fisherlady111 OR from:Snap1967Ginger OR from:AssoJNSPUD OR from:CL4WS_OUT OR from:HagosSuzan OR from:JeffereyJaxen OR from:IanJaeger29 OR from:Mebrat39 OR from:SpacePirate144 OR from:Serenityin24 OR from:SinedWarrior OR from:Freedom_Alley3 OR from:GTV26543476 OR from:zzNFSC OR from:mmtchi OR from:StanVoWales OR from:RikardRene OR from:westcdnfirst OR from:babs4america OR from:N0000024 OR from:MAGAWarrior_45 OR from:BossC_Official OR from:udreams30 OR from:DidierDerichard OR from:doubleDutchquak OR from:bailu_thaifans OR from:Gitmo99 OR from:AmericanwomanU1 OR from:LadyConstance8 OR from:Ms_Betty_Bop OR from:terra_cremada OR from:SparkyBru OR from:SimonElmer2022 OR from:VelzenRemco OR from:Bitcoin1967 OR from:himalayamos OR from:RevolverNewsUSA OR from:AllForYuxin_TH OR from:GuitarJPalumbo OR from:MendlovitzMark OR from:Pwrfulwoman2 OR from:PeteHegseth OR from:AntonioSabatoJr)',
            "tag": "15"},
        {
            "value": 'sample:10 (from:HughBramlett OR from:MikeGil21446788 OR from:patriot_hammer OR from:deSunShineBand OR from:Old_SchoolEddie OR from:sweetcarolinatv OR from:redvoicenews OR from:thekevindeucey OR from:DieHard45RG OR from:TonyIannitelli OR from:WarRoom_FanPage OR from:MtnMama406 OR from:MichaelJaco9 OR from:RayJPolitics1 OR from:ricwe123 OR from:Michael951413 OR from:hottamali02 OR from:patriotmary4 OR from:HouseGOP OR from:YankeeCowboy24 OR from:bennyjohnson OR from:Pdaug44 OR from:tateflixtv OR from:BPartisans OR from:WiktoriaKrasno2 OR from:AscendantDove OR from:czxsdiary OR from:BillEllmore OR from:GigaBeers OR from:KingThorMAGA OR from:JimBobW49 OR from:NickyK1776 OR from:davidharsanyi OR from:Denachtzuster1 OR from:DavidWolfe OR from:nlmedia11 OR from:YasinAslanTrk1 OR from:LionessDeb19 OR from:JessicaLedezmaM OR from:aaronjmate OR from:CShoemakerMD OR from:HCN77777 OR from:guimei2929 OR from:DailyNoahNews OR from:UltraDane OR from:C19VaxInjured OR from:wayvisionnie OR from:PhilHollowayEsq)',
            "tag": "16"},
        {
            "value": 'sample:10 (from:disclosetv OR from:AnnAmericaFirst OR from:OnmyojiWiki_EN OR from:SaltyGoat17 OR from:JackMedia7 OR from:Wondercri1982 OR from:MarieNat23 OR from:TheDAGWOOD13 OR from:JAG582000 OR from:mdt546 OR from:MojaMojappa OR from:moshuixiang OR from:4mYeeFHhA6H1OnF OR from:helen44767171 OR from:nedryun OR from:DaAcervo OR from:weizhenshe OR from:MGKoreaHA OR from:CPAJim2022 OR from:reneeAZpatriot4 OR from:NFSC_HAGnews OR from:sues86453 OR from:kung_fu_jedi OR from:PopsBackAgain OR from:lp_mitchell2 OR from:Censored4sure OR from:ZombyWoof2022 OR from:ryouzi_r OR from:DameScorpio OR from:PatPetterson2 OR from:AllBiteNoBark88 OR from:Xx17965797N OR from:MicheliniSuzie OR from:DelanoSquires OR from:Rammie24 OR from:pamhuntersmom OR from:DeSantisWarRoom OR from:AnnOutLoud OR from:BobFighter_45 OR from:TrevorJukes1 OR from:Jules5570 OR from:RobinOutLoud OR from:jathorpmfm OR from:AdamShawNY OR from:fengyunshe OR from:nho82897178 OR from:Czesc45 OR from:PamelaGeller OR from:barnrble OR from:lawrie_dr)',
            "tag": "17"},
        {
            "value": 'sample:10 (from:DowdEdward OR from:MapleSyrupTart OR from:KyleSeraphin OR from:BossNoeul_TH OR from:ichibeiQ OR from:VeBo1991 OR from:OxfordSevenStar OR from:SamGh1960 OR from:ExtractsUK OR from:carolinagirl_45 OR from:lucaforsure OR from:itismeindy500 OR from:SpartaJustice OR from:exthepose OR from:DiedSuddenly_ OR from:RealDaveCares4u OR from:DbbTom OR from:Threeefer OR from:Revwwthompson OR from:_SmokeyGirl25 OR from:Fortfts_Korea OR from:NoeulOfficial02 OR from:HarperLee6557 OR from:RosannaM1970 OR from:Teagan1776 OR from:Myltraduction OR from:JewelsJonesLive OR from:reBurningBright OR from:realouMAGAgirl OR from:NancyMar2022 OR from:DevilD0g_ OR from:c_plushie OR from:jessies_now OR from:FreeThankElon OR from:PeriklesGREAT OR from:miguelifornia OR from:nfscweizhen OR from:Tex2_A OR from:MAGAIncWarRoom OR from:SystemUpdate_ OR from:TerrenceBeBack OR from:anguishoflibs OR from:HinduNarendra1 OR from:iammichelle777 OR from:Sapnakhatri16_ OR from:Patrici10834779 OR from:patel_patriot OR from:MrsScotty1)',
            "tag": "18"},
        {
            "value": 'sample:10 (from:MosWriting OR from:JoeDelfino9 OR from:NFSCSpeak OR from:moranyibo_ OR from:BuzzPatterson OR from:Kingston_Truth OR from:Anais_Tea_ OR from:DiscoverTRW OR from:RedState66 OR from:ggreenwald OR from:stillgray OR from:JulieGMinistry OR from:bamajayt OR from:Weaponization OR from:Kerfree17 OR from:Thaiku789 OR from:MJTruthUltra OR from:davidcd0418 OR from:larien_gubler OR from:Peoples_Pundit OR from:CurtisHebert OR from:AMJalsevac OR from:MichaelPSenger OR from:ACTforAmerica OR from:MatthewTyrmand OR from:21WIRE OR from:jack_hikuma OR from:80syaku OR from:JaySekulow OR from:frfrankpavone OR from:ShalinGala OR from:SteveDeaceShow OR from:jjauthor OR from:jsmith4966 OR from:TedNugent OR from:mitchellvii OR from:MZHemingway OR from:RealJackHibbs OR from:mcspocky OR from:JudicialWatch OR from:TomFitton OR from:LizCrokin OR from:ProtecttheFaith OR from:JoeBell OR from:RubinReport OR from:kateordie OR from:hodgetwins OR from:JMichaelWaller OR from:PrisonPlanet OR from:Kevin_Shipp OR from:KDuffySr)',
            "tag": "19"},
        {
            "value": 'sample:10 (from:gregreese OR from:JoostNiemoller OR from:toadmeister OR from:PatrickByrne OR from:zerohedge OR from:LifeSite OR from:thewriterme OR from:FAIRImmigration OR from:HoustonKeene OR from:JasonMBrodsky OR from:scrowder OR from:VigilantFox OR from:gatewaypundit OR from:UnzReview OR from:greglaurie OR from:catranchdream OR from:Rasmussen_Poll OR from:JamieSale OR from:AnnCoulter OR from:GUnderground_TV OR from:Scott_4Trump OR from:afshinrattansi OR from:JoeTalkShow OR from:DVATW OR from:rhowardbrowne OR from:theMRC OR from:RealDrGina OR from:ecJulie OR from:SharylAttkisson OR from:denisrancourt OR from:mrddmia OR from:NEWSMAX OR from:JamesMelville OR from:MariaBartiromo OR from:Steve_Sailer OR from:JunkScience OR from:aigkenham OR from:StellaEscoTV OR from:lsferguson OR from:Jamjamisme OR from:JacquiDeevoy1 OR from:koumuzi0622 OR from:respect65 OR from:GLFOP OR from:occupythegetty OR from:AlArabiya_Eng OR from:clif_high OR from:paulturner2012 OR from:atensnut OR from:TuckerCarlson)',
            "tag": "20"},
        {
            "value": 'sample:10 (from:cooltxchick OR from:THEtothe8ight OR from:CortesSteve OR from:HeyTammyBruce OR from:CattHarmony OR from:barnes_law OR from:coffee_anytime OR from:c21markm OR from:stephanieseneff OR from:FatEmperor OR from:christina_bobb OR from:mattletiss7 OR from:john_mcguirk OR from:GenFlynn OR from:SandraYozipovic OR from:SebGorka OR from:TeaPainUSA OR from:GeorgiaLogCabin OR from:MsAvaArmstrong OR from:SwarajyaMag OR from:GarlandNixon OR from:JoeConchaTV OR from:BlueBoxDave OR from:LionelMedia OR from:tracybeanz OR from:RajkumaarPandey OR from:shadygrooove OR from:kimguilfoyle OR from:Patrici15767099 OR from:Jonathan_Cahn OR from:eclipsethis2003 OR from:RMConservative OR from:HeshmatAlavi OR from:hugh_mankind OR from:TaraServatius OR from:Rattetytat OR from:BernardKerik OR from:GR26Sic18 OR from:TheMenzoid OR from:ClimateRealists OR from:ShannonJoyRadio OR from:DanKEberhart OR from:CrimeWatchMpls OR from:1mZerOCool OR from:NedaaAlkhamis OR from:Liz_Wheeler OR from:LouDobbs OR from:robertjlundberg)',
            "tag": "21"},
        {
            "value": 'sample:10 (from:realjusthuman OR from:BhadraPunchline OR from:EricMMatheny OR from:vdare OR from:bluemoon2466 OR from:NetZeroWatch OR from:lesleyabravanel OR from:johncardillo OR from:umekei1113 OR from:VerdadeseNadaMa OR from:stratpol_site OR from:WayneDupreeShow OR from:joyreaper OR from:MrAndyNgo OR from:ClimateDepot OR from:news18dotcom OR from:julie_kelly2 OR from:VLongobardo OR from:stanpcfl OR from:cathyyoung421 OR from:naomirwolf OR from:defjsuh OR from:DiamondandSilk OR from:luking0420 OR from:charliekirk11 OR from:prasannavishy OR from:The_FJC OR from:LionHearted76 OR from:Obamasshadow OR from:fairymochisung OR from:RebelNewsOnline OR from:fieryglimmer OR from:TheClayClark OR from:ArchKennedy OR from:AlphaNewsMN OR from:realMikeLindell OR from:AnAthenianToLDN OR from:NBSaphierMD OR from:SM_NCT OR from:dom_lucre OR from:OffGuardian0 OR from:iheartmindy OR from:Nidhi OR from:KatieDaviscourt OR from:KerriRawson OR from:kylenabecker OR from:jaemin_th OR from:AimHardoi OR from:starstuded11)',
            "tag": "22"},
        {
            "value": 'sample:10 (from:thehealthb0t OR from:truedream416 OR from:ColumbiaBugle OR from:ICRscience OR from:EndGameWW3 OR from:silvano_trotta OR from:lancewallnau OR from:stephphilip8 OR from:Cobratate OR from:RyLiberty OR from:iluminatibot OR from:genuke1 OR from:Mondoweiss OR from:PetsRescues OR from:TimRunsHisMouth OR from:MAGA__Patriot OR from:MMelinda777 OR from:yohiobaseball OR from:BusyDrT OR from:ElijahSchaffer OR from:DavidJHarrisJr OR from:Infocadl2015 OR from:Blue22Dave OR from:Cernovich OR from:Shawn_Farash OR from:seanmdav OR from:Alphafox78 OR from:SoniaPoulton OR from:stkirsch OR from:Breaking911 OR from:Quillette OR from:mtaibbi OR from:marklevinshow OR from:MeganFoxWriter OR from:RichSementa OR from:bunnyboxz OR from:JKash000 OR from:WylieGuide OR from:DonaldJTrumpJr OR from:giga128daytoy OR from:ufob0t OR from:brigrey1005 OR from:News18Showsha OR from:EconomicTimes OR from:RWMaloneMD OR from:Lilytail_D OR from:RSBNetwork OR from:WhitlockJason OR from:prageru OR from:seanhannity)',
            "tag": "23"},
        {
            "value": 'sample:10 (from:coasttocoastam OR from:CRRJA5 OR from:kksheld OR from:DavidBCollum OR from:amuse OR from:swilkinsonbc OR from:21stCenturyWire OR from:March_for_Life OR from:NashvilleTea OR from:mmintt_ssamm OR from:andweknow OR from:AmanKayamHai_ OR from:Franklin_Graham OR from:JohnMappin OR from:SGTreport OR from:FiorellaIsabelM OR from:0ccultbot OR from:MaajidNawaz OR from:paulbenedict7 OR from:BoSnerdley OR from:RogerJStoneJr OR from:DrAseemMalhotra OR from:w_terrence OR from:ChuckCallesto OR from:ToscaAusten OR from:ByronYork OR from:XZFCTH1005 OR from:BPUnion OR from:TheGrayzoneNews OR from:TFL1728 OR from:LuvusicaJ OR from:imjustasteph OR from:Bipartisanism OR from:nbreavington OR from:drcraigwax OR from:judyannaggie OR from:PatriotaWil OR from:JFlippo1327 OR from:globaltimesnews OR from:tomselliott OR from:alexbruesewitz OR from:TexasLindsay_ OR from:LifeNewsHQ OR from:augustosnunes OR from:nancyvictoria OR from:IngrahamAngle OR from:taradublinrocks OR from:steelpoleman OR from:jsolomonReports)',
            "tag": "24"},
        {
            "value": 'sample:10 (from:GeorgeMurrayJr1 OR from:alx OR from:ikeTrump555 OR from:LauraLoomer OR from:MaxBlumenthal OR from:JohnRLottJr OR from:hrkbenowen OR from:curryja OR from:RNCResearch OR from:VlogdoLisboa OR from:LarrySchweikart OR from:timand2037 OR from:abirballan OR from:RealDrJaneRuby OR from:BrianMGC OR from:sneako OR from:libertytarian OR from:JackPosobiec OR from:TheLastRefuge2 OR from:mcdtournesol OR from:RossRosenfeld OR from:andy5_123 OR from:RealMattCouch OR from:Hamletgarcia17 OR from:USAWatchdog OR from:eduardomenoni OR from:AlamoPong OR from:USA_Anne711 OR from:RT_com OR from:CNNnews18 OR from:JohnBasham OR from:GMWatch OR from:TheChiefNerd OR from:RealGeoEngWatch OR from:ashoswai OR from:LilaGraceRose OR from:PeterSweden7 OR from:wattsupwiththat OR from:LennyDykstra OR from:ACTBrigitte OR from:dpadams6 OR from:ASimplePatriot OR from:TeamTrump OR from:wonderworld2016 OR from:cosmicruiser OR from:MikeSwadling OR from:j_sato OR from:DOYOUNG__21 OR from:BullseyeBanjo OR from:paulsperry_)',
            "tag": "25"},
        {
            "value": 'sample:10 (from:BeachCity55 OR from:LifeNewsToo OR from:LiberatedCit OR from:vgclements1 OR from:TonyHinton2016 OR from:BlazeTV OR from:LaraLeaTrump OR from:Cam_Cawthorne OR from:realLizUSA OR from:PJMedia_com OR from:LawrenceSellin OR from:REMASCULATE OR from:ProfMJCleveland OR from:TOMRJZSR OR from:JennaEllisEsq OR from:StopTechnocracy OR from:TAG2335 OR from:ChildrensHD OR from:lovetocook12345 OR from:RobertoCarlo14 OR from:SandalsAnew OR from:universalsoftw2 OR from:lawyer4laws OR from:misskloss OR from:rycunni OR from:Leyh___Brian OR from:piyococcochan2 OR from:StevePieczenik OR from:Wendyy2009Wendy OR from:Therealbp65 OR from:DFBHarvard OR from:rumblevideo OR from:Panamadan61 OR from:ProudElephantUS OR from:republic OR from:Krieger66362259 OR from:Tamama0306 OR from:lukkana851 OR from:AlternatNews OR from:Lisahudsonchow7 OR from:TrumpTrackerJP OR from:richardursomd OR from:VivaLaAmes11 OR from:JustinTHaskins OR from:Tushar15_ OR from:dramapotatoe OR from:sicgom_esports OR from:ganaha_masako)',
            "tag": "26"},
        {
            "value": 'sample:10 (from:Anpo_Star OR from:CEcoupe OR from:IndoPac_Info OR from:Nicoletta0602 OR from:VDejan0000 OR from:jjarchiv OR from:Project_Veritas OR from:NextRevFNC OR from:MinnesotaMiners OR from:HighWireTalk OR from:robinmonotti OR from:DollArntzen OR from:emeriticus OR from:EndRaceHating OR from:dilireba_ OR from:srasberry1 OR from:TPPatriots OR from:steve_hanke OR from:JJDJ1187 OR from:HowardSteen4 OR from:viniciuscfp82 OR from:brenda_spiller OR from:RienNavelpluis OR from:white_arrow_uk OR from:DC_Draino OR from:StudioAdmin OR from:ChinaDaily OR from:WildlifeRefugee OR from:OccupyDemocrats OR from:brandootr OR from:Elvin_Unleashed OR from:kimura_kenchin OR from:Jrg52192342 OR from:JoTrumpCA OR from:LSNCatholic OR from:fordmb1 OR from:RichardStiller4 OR from:CoffindafferFBI OR from:JohnBoweActor OR from:Lowcountry1Girl OR from:1028WINWIN_TH OR from:greg_price11 OR from:bainjal OR from:republic_glitz OR from:TommyPigott OR from:CassandraRules OR from:SandraSBreen OR from:groth1945 OR from:Eunhae0404_1510)',
            "tag": "27"}
    ]
    payload = {"add": sample_rules}
    response = requests.post(
        "https://api.twitter.com/2/tweets/search/stream/rules",
        auth=bearer_oauth,
        json=payload,
    )
    if response.status_code != 201:
        raise Exception(
            "Cannot add rules (HTTP {}): {}".format(response.status_code, response.text)
        )
    print(json.dumps(response.json()))


def get_stream(set):
    response = requests.get(
        "https://api.twitter.com/2/tweets/search/stream", auth=bearer_oauth, params=tweet_params, stream=True,
    )
    print(response.status_code)
    if response.status_code != 200:
        raise Exception(
            "Cannot get stream (HTTP {}): {}".format(
                response.status_code, response.text
            )
        )
    for response_line in response.iter_lines():
        if response_line:
            json_response = json.loads(response_line)
            ff.write(str(json_response))
            ff.write('\n')


def main():
    rules = get_rules()
    delete = delete_all_rules(rules)
    set = set_rules(delete)
    get_stream(set)


if __name__ == "__main__":
    main()
